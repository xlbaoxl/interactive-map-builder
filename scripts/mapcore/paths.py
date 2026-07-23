"""Locate runtime resources in a Skill checkout or an installed wheel."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    checkout = Path(__file__).resolve().parents[2]
    if (
        (checkout / "assets" / "templates").is_dir()
        and (checkout / "references" / "map-spec.schema.json").is_file()
    ):
        return checkout
    installed = Path(sys.prefix) / "share" / "interactive-map-builder"
    if (
        (installed / "assets" / "templates").is_dir()
        and (installed / "references" / "map-spec.schema.json").is_file()
    ):
        return installed
    raise FileNotFoundError(
        "Interactive Map Builder resources were not found in the checkout or installation."
    )


__all__ = ["resource_root"]
