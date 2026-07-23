"""Reliable, auditable ArcGIS FeatureServer acquisition."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

import requests

PathLike = Union[str, Path]


class ArcGISError(RuntimeError):
    """Raised when a service response cannot produce a complete local copy."""


@dataclass(frozen=True)
class ArcGISDownloadResult:
    output_path: Path
    provenance_path: Path
    object_id_field: str
    expected_count: int
    downloaded_count: int
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["output_path"] = str(self.output_path)
        result["provenance_path"] = str(self.provenance_path)
        return result


def _query_url(service_url: str) -> str:
    parts = urlsplit(service_url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ArcGISError("ArcGIS URL must be an absolute HTTP(S) URL.")
    path = parts.path.rstrip("/")
    if not path.lower().endswith("/query"):
        path += "/query"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def _public_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _retry_delay(response: Any, attempt: int) -> float:
    headers = getattr(response, "headers", {}) or {}
    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.0), 30.0)
        except (TypeError, ValueError):
            pass
    return min(0.5 * (2**attempt), 8.0)


def _request_json(
    session: Any,
    url: str,
    params: Mapping[str, Any],
    *,
    timeout: float,
    max_retries: int,
    sleep_fn: Callable[[float], None],
) -> Dict[str, Any]:
    last_error: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        response = None
        try:
            response = session.get(url, params=dict(params), timeout=timeout)
            status = int(getattr(response, "status_code", 200))
            if status >= 400:
                raise requests.HTTPError("HTTP {}".format(status), response=response)
            payload = response.json()
            if not isinstance(payload, dict):
                raise ArcGISError("ArcGIS response was not a JSON object.")
            if "error" in payload:
                error = payload.get("error") or {}
                code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
                message = (
                    error.get("message", "ArcGIS service error")
                    if isinstance(error, dict)
                    else str(error)
                )
                details = error.get("details", []) if isinstance(error, dict) else []
                detail_text = "; ".join(str(value) for value in details if value)
                full_message = "ArcGIS error {}: {}{}".format(
                    code, message, " ({})".format(detail_text) if detail_text else ""
                )
                try:
                    retryable = int(code) == 429 or int(code) >= 500
                except (TypeError, ValueError):
                    retryable = False
                if retryable:
                    raise requests.HTTPError(full_message, response=response)
                raise ArcGISError(full_message)
            return payload
        except ArcGISError:
            raise
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            status = int(getattr(response, "status_code", 0)) if response is not None else 0
            retryable = response is None or status == 429 or status >= 500
            if not retryable or attempt >= max_retries:
                break
            sleep_fn(_retry_delay(response, attempt))
    raise ArcGISError(
        "ArcGIS request failed after {} attempt(s): {}".format(max_retries + 1, last_error)
    ) from last_error


def _id_key(value: Any) -> Tuple[int, Any]:
    if isinstance(value, bool):
        return (1, str(value))
    if isinstance(value, (int, float)):
        return (0, value)
    text = str(value)
    try:
        return (0, int(text))
    except ValueError:
        return (1, text)


def _canonical_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _feature_object_id(feature: Mapping[str, Any], field: str) -> Any:
    properties = feature.get("properties")
    if isinstance(properties, Mapping):
        if field in properties:
            return properties[field]
        field_casefold = field.casefold()
        for name, value in properties.items():
            if str(name).casefold() == field_casefold:
                return value
    if "id" in feature:
        return feature["id"]
    return None


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, str(path))
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return hashlib.sha256(encoded).hexdigest()


def download_feature_service(
    service_url: str,
    output_path: PathLike,
    *,
    where: str = "1=1",
    out_fields: Union[str, Sequence[str]] = "*",
    batch_size: int = 200,
    timeout: float = 30.0,
    max_retries: int = 3,
    provenance_path: Optional[PathLike] = None,
    session: Optional[Any] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> ArcGISDownloadResult:
    """Download every FeatureServer record through a stable object-ID plan.

    The service is queried for count and object IDs first. Features are then
    requested in deterministic object-ID chunks and checked for missing,
    duplicate, or unexpected records before either output file is written.
    """

    if not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")
    if not where or not str(where).strip():
        raise ValueError("where must be a non-empty SQL expression")

    query_url = _query_url(service_url)
    client = session or requests.Session()

    ids_payload = _request_json(
        client,
        query_url,
        {"f": "json", "where": where, "returnIdsOnly": "true"},
        timeout=timeout,
        max_retries=max_retries,
        sleep_fn=sleep_fn,
    )
    object_id_field = ids_payload.get("objectIdFieldName") or ids_payload.get("objectIdField")
    if not object_id_field or not isinstance(object_id_field, str):
        raise ArcGISError("returnIdsOnly response did not declare objectIdFieldName.")
    raw_ids = ids_payload.get("objectIds")
    if raw_ids is None:
        raise ArcGISError("returnIdsOnly response did not contain objectIds.")
    if not isinstance(raw_ids, list):
        raise ArcGISError("returnIdsOnly objectIds must be a list.")

    canonical_ids = [_canonical_id(value) for value in raw_ids]
    if any(not value for value in canonical_ids):
        raise ArcGISError("returnIdsOnly response contained a null object ID.")
    if len(set(canonical_ids)) != len(canonical_ids):
        raise ArcGISError("returnIdsOnly response contained duplicate object IDs.")
    object_ids = sorted(raw_ids, key=_id_key)

    count_payload = _request_json(
        client,
        query_url,
        {"f": "json", "where": where, "returnCountOnly": "true"},
        timeout=timeout,
        max_retries=max_retries,
        sleep_fn=sleep_fn,
    )
    count = count_payload.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ArcGISError("returnCountOnly response did not contain a valid count.")
    if count != len(object_ids):
        raise ArcGISError(
            "ArcGIS count mismatch before download: count={}, objectIds={}.".format(
                count, len(object_ids)
            )
        )

    if isinstance(out_fields, str):
        fields_value = out_fields
        provenance_fields: Union[str, List[str]] = out_fields
    else:
        field_list = [str(field) for field in out_fields]
        if not field_list:
            raise ValueError("out_fields cannot be empty")
        fields_value = ",".join(field_list)
        provenance_fields = field_list

    features_by_id: Dict[str, Dict[str, Any]] = {}
    for start in range(0, len(object_ids), batch_size):
        batch = object_ids[start : start + batch_size]
        payload = _request_json(
            client,
            query_url,
            {
                "f": "geojson",
                "objectIds": ",".join(str(value) for value in batch),
                "outFields": fields_value,
                "returnGeometry": "true",
                "outSR": "4326",
            },
            timeout=timeout,
            max_retries=max_retries,
            sleep_fn=sleep_fn,
        )
        if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
            raise ArcGISError("Feature query did not return a GeoJSON FeatureCollection.")
        if payload.get("exceededTransferLimit"):
            raise ArcGISError("Feature query exceeded the service transfer limit.")
        expected_batch = {_canonical_id(value) for value in batch}
        for feature in payload["features"]:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ArcGISError("Feature query returned a malformed GeoJSON feature.")
            object_id = _canonical_id(_feature_object_id(feature, object_id_field))
            if not object_id:
                raise ArcGISError(
                    "Downloaded feature is missing object ID field {!r}.".format(object_id_field)
                )
            if object_id not in expected_batch:
                raise ArcGISError("Downloaded unexpected object ID: {}.".format(object_id))
            if object_id in features_by_id:
                raise ArcGISError("Downloaded duplicate object ID: {}.".format(object_id))
            features_by_id[object_id] = feature

    expected_ids = {_canonical_id(value) for value in object_ids}
    downloaded_ids = set(features_by_id)
    missing = sorted(expected_ids - downloaded_ids, key=_id_key)
    unexpected = sorted(downloaded_ids - expected_ids, key=_id_key)
    if missing or unexpected or len(features_by_id) != count:
        details = []
        if missing:
            details.append("missing={}".format(",".join(missing[:10])))
        if unexpected:
            details.append("unexpected={}".format(",".join(unexpected[:10])))
        details.append("expected_count={}".format(count))
        details.append("downloaded_count={}".format(len(features_by_id)))
        raise ArcGISError("ArcGIS feature mismatch: {}.".format("; ".join(details)))

    ordered_features = [
        features_by_id[_canonical_id(object_id)] for object_id in object_ids
    ]
    collection = {"type": "FeatureCollection", "features": ordered_features}

    destination = Path(output_path).expanduser().resolve()
    provenance_destination = (
        Path(provenance_path).expanduser().resolve()
        if provenance_path is not None
        else destination.with_suffix(destination.suffix + ".provenance.json")
    )
    output_sha = _write_json_atomic(destination, collection)
    provenance = {
        "schema_version": "1.0",
        "source_url": _public_url(service_url),
        "query_url": _public_url(query_url),
        "where": where,
        "out_fields": provenance_fields,
        "object_id_field": object_id_field,
        "expected_count": count,
        "downloaded_count": len(ordered_features),
        "batch_size": batch_size,
        "output_file": destination.name,
        "output_sha256": output_sha,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _write_json_atomic(provenance_destination, provenance)

    return ArcGISDownloadResult(
        output_path=destination,
        provenance_path=provenance_destination,
        object_id_field=object_id_field,
        expected_count=count,
        downloaded_count=len(ordered_features),
        sha256=output_sha,
    )


# Public command-oriented alias.
fetch_arcgis = download_feature_service
