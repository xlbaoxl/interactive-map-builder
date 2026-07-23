import json

import pytest
import requests

from scripts.mapcore.arcgis import ArcGISError, download_feature_service


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


class RoutingSession:
    def __init__(self, *, ids=(3, 1, 2), count=None, fail_once=False):
        self.ids = list(ids)
        self.count = len(ids) if count is None else count
        self.fail_once = fail_once
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, dict(params), timeout))
        if self.fail_once:
            self.fail_once = False
            raise requests.ConnectionError("temporary")
        if params.get("returnIdsOnly") == "true":
            return FakeResponse(
                {"objectIdFieldName": "OBJECTID", "objectIds": self.ids}
            )
        if params.get("returnCountOnly") == "true":
            return FakeResponse({"count": self.count})
        requested = [int(value) for value in params["objectIds"].split(",")]
        # Reverse server order: the downloader must restore object-ID order.
        features = [
            {
                "type": "Feature",
                "properties": {"OBJECTID": object_id, "名称": "要素{}".format(object_id)},
                "geometry": {"type": "Point", "coordinates": [object_id, 0]},
            }
            for object_id in reversed(requested)
        ]
        return FakeResponse({"type": "FeatureCollection", "features": features})


def test_arcgis_download_is_paged_sorted_and_audited(tmp_path):
    session = RoutingSession()
    output = tmp_path / "features.geojson"
    result = download_feature_service(
        "https://example.test/FeatureServer/0",
        output,
        batch_size=2,
        session=session,
        sleep_fn=lambda _: None,
    )

    collection = json.loads(output.read_text(encoding="utf-8"))
    assert [feature["properties"]["OBJECTID"] for feature in collection["features"]] == [
        1,
        2,
        3,
    ]
    assert result.expected_count == result.downloaded_count == 3
    assert len(result.sha256) == 64
    provenance = json.loads(result.provenance_path.read_text(encoding="utf-8"))
    assert provenance["source_url"] == "https://example.test/FeatureServer/0"
    assert provenance["expected_count"] == 3
    assert provenance["output_sha256"] == result.sha256

    feature_calls = [
        params for _, params, _ in session.calls if params.get("f") == "geojson"
    ]
    assert [params["objectIds"] for params in feature_calls] == ["1,2", "3"]
    assert all(params["outSR"] == "4326" for params in feature_calls)


def test_arcgis_retries_transient_connection_error(tmp_path):
    session = RoutingSession(ids=(1,), fail_once=True)
    pauses = []

    result = download_feature_service(
        "https://example.test/FeatureServer/0/query",
        tmp_path / "one.geojson",
        session=session,
        max_retries=1,
        sleep_fn=pauses.append,
    )

    assert result.downloaded_count == 1
    assert pauses == [0.5]


def test_arcgis_rejects_count_mismatch_without_writing(tmp_path):
    session = RoutingSession(ids=(1, 2), count=3)
    output = tmp_path / "bad.geojson"

    with pytest.raises(ArcGISError, match="count mismatch"):
        download_feature_service(
            "https://example.test/FeatureServer/0",
            output,
            session=session,
            sleep_fn=lambda _: None,
        )

    assert not output.exists()


def test_arcgis_rejects_duplicate_ids_before_downloading(tmp_path):
    output = tmp_path / "bad.geojson"
    with pytest.raises(ArcGISError, match="duplicate object IDs"):
        download_feature_service(
            "https://example.test/FeatureServer/0",
            output,
            session=RoutingSession(ids=(1, 1)),
            sleep_fn=lambda _: None,
        )
    assert not output.exists()


class MissingFeatureSession(RoutingSession):
    def get(self, url, params, timeout):
        response = super().get(url, params, timeout)
        if params.get("f") == "geojson":
            response._payload["features"] = []
        return response


def test_arcgis_rejects_missing_downloaded_features(tmp_path):
    output = tmp_path / "missing.geojson"
    with pytest.raises(ArcGISError, match="feature mismatch"):
        download_feature_service(
            "https://example.test/FeatureServer/0",
            output,
            session=MissingFeatureSession(ids=(1,)),
            sleep_fn=lambda _: None,
        )
    assert not output.exists()


class ErrorSession:
    def get(self, url, params, timeout):
        return FakeResponse(
            {"error": {"code": 400, "message": "Bad query", "details": ["bad field"]}}
        )


def test_arcgis_surfaces_service_errors(tmp_path):
    with pytest.raises(ArcGISError, match="Bad query.*bad field"):
        download_feature_service(
            "https://example.test/FeatureServer/0",
            tmp_path / "error.geojson",
            session=ErrorSession(),
            sleep_fn=lambda _: None,
        )


def test_arcgis_validates_arguments(tmp_path):
    with pytest.raises(ValueError, match="batch_size"):
        download_feature_service(
            "https://example.test/FeatureServer/0",
            tmp_path / "x.geojson",
            batch_size=0,
        )
    with pytest.raises(ArcGISError, match="absolute HTTP"):
        download_feature_service("not-a-url", tmp_path / "x.geojson")
