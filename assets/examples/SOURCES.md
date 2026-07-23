# Example data sources

The README examples use fixed, local snapshots of public datasets from
[NYC Open Data](https://opendata.cityofnewyork.us/). Builds and tests never fetch
these datasets at runtime.

Snapshot date: **2026-07-23**

## Searchable park catalog

- Dataset: [Parks Properties (`enfh-gkve`)](https://data.cityofnewyork.us/d/enfh-gkve)
- Publisher: New York City Department of Parks and Recreation
- Selection: records where `BOROUGH = M`, `RETIRED = false`, and `ACRES >= 20`
- Result: 18 Manhattan park properties
- Fields retained: stable GIS object ID, sign name, type, acreage, waterfront flag,
  and location description

## Multilayer city map

- Boundary: [Borough Boundaries (`gthc-hcne`)](https://data.cityofnewyork.us/d/gthc-hcne),
  published by the New York City Department of City Planning; Manhattan only
- Lines: [New York City Bike Routes (`mzxg-pwib`)](https://data.cityofnewyork.us/d/mzxg-pwib),
  published by the New York City Department of Transportation; current Manhattan
  segments clipped to the borough boundary and dissolved into the four official
  facility-class codes
- Points: [Public Restrooms (`i7jb-7jku`)](https://data.cityofnewyork.us/d/i7jb-7jku),
  published by NYC agencies and public library systems; operational Manhattan
  facilities outside parks, with deterministic IDs derived from name, type, and
  coordinates

## Processing and terms

- All outputs are stored as GeoJSON in EPSG:4326 / CRS84.
- Line and polygon geometry was made valid and simplified at 15 feet in
  EPSG:2263 before reprojection. Coordinates were snapped to 7 decimal places
  with validity-preserving precision reduction.
- Only the display and provenance fields needed by the examples are retained.
- The snapshots are redistributed under the
  [NYC Open Data Terms of Use](https://opendata.cityofnewyork.us/overview/#termsofuse).
- Run `python scripts/prepare_readme_examples.py` from the repository root to
  refresh the snapshots. Review resulting data and counts before committing an
  update because upstream datasets can change.
