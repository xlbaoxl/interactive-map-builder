from __future__ import annotations

import csv
import json
from pathlib import Path

import geopandas as gpd

from mapcore.loaders import load_source
from mapcore.spec import load_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"


def test_all_example_specs_validate_and_sources_exist() -> None:
    specs = sorted(EXAMPLES.glob("*/map_spec.json"))
    assert [path.parent.name for path in specs] == [
        "csv-points",
        "linked-by-id",
        "map-list",
        "multilayer",
    ]

    for path in specs:
        spec, base_dir = load_spec(path)
        assert spec["schema_version"] == "1.0"
        for layer in spec["layers"]:
            source = base_dir / layer["source"]["path"]
            assert source.is_file(), source
            assert not Path(layer["source"]["path"]).is_absolute()
            frame = load_source(layer["source"], base_dir=base_dir)
            assert not frame.empty
            assert frame.crs is not None


def test_geojson_examples_have_crs_unique_ids_and_known_categories() -> None:
    for path in sorted(EXAMPLES.glob("*/*.geojson")):
        frame = gpd.read_file(path)
        assert not frame.empty
        assert frame.crs is not None
        assert "id" in frame.columns
        assert frame["id"].is_unique
        assert frame.geometry.notna().all()
        assert (~frame.geometry.is_empty).all()
        assert frame.geometry.is_valid.all()

    for spec_path in sorted(EXAMPLES.glob("*/map_spec.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        for layer in spec["layers"]:
            source = spec_path.parent / layer["source"]["path"]
            if source.suffix.lower() != ".geojson":
                continue
            frame = gpd.read_file(source)
            field = layer.get("style", {}).get("color_field")
            categories = layer.get("style", {}).get("categories", {})
            if field:
                assert {str(value) for value in frame[field].dropna().unique()} == set(categories)


def test_linked_by_id_example_is_generic_and_ids_align() -> None:
    example = EXAMPLES / "linked-by-id"
    spec = json.loads((example / "map_spec.json").read_text(encoding="utf-8"))
    with (example / "metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert spec["linked_view"] == {
        "layer": "features",
        "x_field": "x",
        "y_field": "y",
        "title": "Synthetic x/y metrics linked by stable feature id",
    }
    assert len(rows) == 4
    assert len({row["id"] for row in rows}) == len(rows)
    assert all(row["x"] and row["y"] and row["longitude"] and row["latitude"] for row in rows)

    corpus = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in example.iterdir() if path.is_file()
    )
    for forbidden in ("safegraph", "quadrant", "四象限"):
        assert forbidden not in corpus
