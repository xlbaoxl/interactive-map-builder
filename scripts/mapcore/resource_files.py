"""Read immutable runtime files bundled inside the mapcore package."""

from __future__ import annotations

from importlib import resources
from typing import Any


def resource_file(*parts: str) -> Any:
    """Return an importlib Traversable for one bundled resource."""

    target = resources.files("mapcore").joinpath("resources")
    for part in parts:
        target = target.joinpath(part)
    return target


def read_resource_text(*parts: str) -> str:
    """Read a UTF-8 package resource without relying on sys.prefix paths."""

    return resource_file(*parts).read_text(encoding="utf-8")


__all__ = ["read_resource_text", "resource_file"]
