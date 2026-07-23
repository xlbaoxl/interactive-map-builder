"""Load and validate map specifications."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Tuple

from jsonschema import Draft202012Validator

from .paths import resource_root


class SpecError(ValueError):
    """Raised when a map specification is invalid."""


def skill_root() -> Path:
    return resource_root()


def schema_path() -> Path:
    return skill_root() / "references" / "map-spec.schema.json"


def load_schema() -> Dict[str, Any]:
    with schema_path().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_absolute_on_any_platform(value: str) -> bool:
    return (
        Path(value).is_absolute()
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
    )


def _apply_defaults(instance: Any, schema: Dict[str, Any], root: Dict[str, Any]) -> None:
    if "$ref" in schema:
        target: Any = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        _apply_defaults(instance, target, root)
        return
    if isinstance(instance, dict):
        for key, child_schema in schema.get("properties", {}).items():
            if key not in instance and "default" in child_schema:
                instance[key] = deepcopy(child_schema["default"])
            if key in instance:
                _apply_defaults(instance[key], child_schema, root)
    elif isinstance(instance, list):
        item_schema = schema.get("items")
        if item_schema:
            for item in instance:
                _apply_defaults(item, item_schema, root)


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    schema = load_schema()
    resolved = deepcopy(spec)
    _apply_defaults(resolved, schema, schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(resolved), key=lambda e: list(e.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            details.append(f"{location}: {error.message}")
        raise SpecError("Invalid map specification:\n- " + "\n- ".join(details))

    layer_ids = [layer["id"] for layer in resolved["layers"]]
    if len(layer_ids) != len(set(layer_ids)):
        raise SpecError("Layer ids must be unique.")
    absolute_sources = [
        layer["id"]
        for layer in resolved["layers"]
        if _is_absolute_on_any_platform(str(layer["source"]["path"]))
    ]
    if absolute_sources:
        raise SpecError(
            "Source paths must be relative to the specification file: {}".format(
                ", ".join(absolute_sources)
            )
        )
    for key, value in resolved.get("outputs", {}).items():
        output_path = Path(str(value))
        if _is_absolute_on_any_platform(str(value)) or ".." in output_path.parts:
            raise SpecError("outputs.{} must stay inside the selected output directory.".format(key))
    if resolved["template"] == "map-list":
        primary = resolved.get("primary_layer")
        if not primary:
            raise SpecError("map-list requires primary_layer.")
        if primary not in layer_ids:
            raise SpecError(f"primary_layer {primary!r} does not match a layer id.")
    linked = resolved.get("linked_view")
    if linked and linked["layer"] not in layer_ids:
        raise SpecError("linked_view.layer does not match a layer id.")
    return resolved


def load_spec(path: Path) -> Tuple[Dict[str, Any], Path]:
    spec_path = path.resolve()
    with spec_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return validate_spec(raw), spec_path.parent


def write_resolved_spec(spec: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(spec, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
