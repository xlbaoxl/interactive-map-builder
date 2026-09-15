"""Regression tests for lazy imports and optional Excel readers.

Use fresh interpreters: checking sys.modules in a shared pytest process can
miss eager imports performed by unrelated tests during collection.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GIS = ("geopandas", "pandas", "numpy", "shapely", "pyogrio", "matplotlib", "openpyxl", "xlrd")


def _isolated(code: str, blocked=(), env=None):
    guard = f'''
import importlib.abc
import sys
blocked = {tuple(blocked)!r}
class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in blocked:
            raise ModuleNotFoundError("Blocked optional import: " + fullname, name=fullname.split(".")[0])
sys.meta_path.insert(0, BlockImports())
'''
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "scripts")
    environment.update(env or {})
    result = subprocess.run(
        [sys.executable, "-c", guard + "\n" + code], cwd=ROOT,
        env=environment, capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.mark.parametrize("args", [
    ["--version"], ["--help"], ["build", "--help"],
    ["run", "--help"], ["doctor", "--help"],
])
def test_metadata_and_help_work_without_runtime_dependencies(args):
    result = _isolated(
        f"from cli import main\nmain({args!r})",
        blocked=GIS + ("jsonschema", "jinja2", "requests"),
    )
    assert result.stdout.strip()


def test_disabled_update_preflight_works_without_gis(tmp_path):
    result = _isolated(
        'from cli import main\nassert main(["update", "--preflight"]) == 0',
        blocked=GIS,
        env={"IMB_DISABLE_AUTO_UPDATE": "1", "IMB_UPDATE_STATE": str(tmp_path / "state.json")},
    )
    assert json.loads(result.stdout)["status"] == "disabled"


def test_doctor_reports_missing_core_dependencies_as_json():
    result = _isolated('''
import contextlib, io, json
from cli import main
error = io.StringIO()
with contextlib.redirect_stderr(error):
    status = main(["doctor"])
assert status == 2
assert json.loads(error.getvalue())["status"] == "fail"
''', blocked=GIS)
    assert not result.stderr


def test_offline_doctor_does_not_load_plotting_or_excel():
    result = _isolated('''
import json, sys
from cli import run_doctor
result = run_doctor()
assert result["status"] == "pass"
assert result["network_used"] is False
assert not any(name.split(".")[0] in blocked for name in sys.modules)
print(json.dumps(result))
''', blocked=("matplotlib", "openpyxl", "xlrd"))
    assert json.loads(result.stdout)["feature_count"] == 2


def test_public_lazy_exports_preserve_identity():
    _isolated('''
import mapcore
assert "normalize_geodata" in dir(mapcore)
assert "geopandas" not in sys.modules
from mapcore import normalize_geodata, load_source, ValidationError, current_schema_version
from mapcore.normalize import normalize_geodata as canonical
assert normalize_geodata is canonical
assert mapcore.normalize_geodata is canonical
assert current_schema_version() == "1.2"
try:
    mapcore.does_not_exist
except AttributeError:
    pass
else:
    raise AssertionError("Unknown export should raise AttributeError")
''')


@pytest.mark.parametrize("suffix,engine", [(".xlsx", "openpyxl"), (".xls", "xlrd")])
@pytest.mark.parametrize("operation", ["inspect", "load"])
def test_missing_excel_readers_have_actionable_errors(tmp_path, suffix, engine, operation):
    source = tmp_path / ("places" + suffix)
    source.write_bytes(b"Reader availability is checked before workbook parsing.")
    _isolated(f'''
from mapcore.inspect_data import inspect_inputs
from mapcore.loaders import DataLoadError, load_geodata
try:
    if {operation!r} == "inspect":
        inspect_inputs([{str(source)!r}])
    else:
        load_geodata({str(source)!r}, lon_field="lon", lat_field="lat", crs="EPSG:4326")
except DataLoadError as exc:
    assert {engine!r} in str(exc)
    assert '.[excel]' in str(exc)
else:
    raise AssertionError("Missing reader should stop the operation")
''', blocked=(engine,))


def test_broken_reader_dependency_is_not_masked(monkeypatch):
    import mapcore.loaders as loaders
    def broken_import(name):
        raise ModuleNotFoundError("Broken transitive dependency", name="reader_dependency")
    monkeypatch.setattr(loaders, "import_module", broken_import)
    with pytest.raises(ModuleNotFoundError, match="transitive dependency"):
        loaders.excel_engine(Path("places.xlsx"))


@pytest.mark.parametrize("colors", [["#ffffff", "#0000ff"], ["red", "blue"], ["tab:blue", "tab:orange"]])
@pytest.mark.parametrize("count", [1, 3, 5, 7])
def test_interpolated_palette_semantics_remain_unchanged(colors, count):
    from matplotlib.colors import LinearSegmentedColormap, to_hex
    from mapcore.style import _colors
    cmap = LinearSegmentedColormap.from_list("previous-behavior", colors)
    samples = [0.5] if count == 1 else [i / (count - 1) for i in range(count)]
    expected = [to_hex(cmap(value), keep_alpha=False) for value in samples]
    assert _colors(colors, count) == expected


def test_already_sized_palette_needs_no_matplotlib():
    _isolated('''
from mapcore.style import _colors
assert _colors(["red", "blue"], 2) == ["red", "blue"]
assert "matplotlib" not in sys.modules
''', blocked=("matplotlib",))


@pytest.mark.parametrize("template", ["map-list", "multilayer"])
def test_resolved_multilayer_intent_builds_via_cli(tmp_path, template, capsys):
    from cli import main
    from map_builder import verify_dist
    sources = []
    for name in ("facilities", "context"):
        source = tmp_path / (name + ".csv")
        source.write_text(
            "id,name,type,lon,lat\nA,North,service,118.1,39.6\nB,South,entry,118.2,39.7\n",
            encoding="utf-8",
        )
        sources.append(str(source))
    dist = tmp_path / "dist"
    args = ["run", *sources, "--template", template, "--crs", "EPSG:4326",
            "--x", "lon", "--y", "lat", "--locale", "zh-CN", "--output", str(dist)]
    if template == "map-list":
        args += ["--primary-layer", "facilities"]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "pass"
    assert result["template"] == template
    spec = json.loads((dist / "map_spec.json").read_text(encoding="utf-8"))
    assert spec["template"] == template
    assert len(spec["layers"]) == 2
    if template == "map-list":
        assert spec["primary_layer"] == "facilities"
    report = json.loads((dist / "build_report.json").read_text(encoding="utf-8"))
    assert report["performance"]["feature_count"] == 4
    assert verify_dist(dist)["status"] == "pass"
    assert not any(dist.glob("*.png"))
