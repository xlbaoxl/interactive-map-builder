from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point

from mapcore.style import StyleError, resolve_layer_style


def _frame() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"score": [1.0, 2.0, 3.0, 4.0, None]},
        geometry=[Point(index, index) for index in range(5)],
        crs="EPSG:4326",
    )


@pytest.mark.parametrize("method", ["quantile", "equal_interval"])
def test_graduated_style_resolves_shared_categories(method: str) -> None:
    frame, layer, report = resolve_layer_style(
        _frame(),
        {
            "id": "scores",
            "style": {
                "mode": "graduated",
                "field": "score",
                "method": method,
                "classes": 3,
                "colors": ["#ffffff", "#0000ff"],
            },
        },
    )
    field = layer["style"]["color_field"]
    assert field in frame.columns
    assert report["resolved_classes"] == len(report["breaks"]) - 1
    assert layer["style"]["categories"] == report["categories"]
    assert "未分类 / Missing" in report["categories"]
    assert set(frame[field].dropna()) == set(report["categories"])


def test_custom_breaks_must_cover_observed_values() -> None:
    with pytest.raises(StyleError, match="full observed value range"):
        resolve_layer_style(
            _frame(),
            {
                "id": "scores",
                "style": {
                    "mode": "graduated",
                    "field": "score",
                    "method": "custom_breaks",
                    "breaks": [1.5, 2.5, 3.5],
                },
            },
        )
