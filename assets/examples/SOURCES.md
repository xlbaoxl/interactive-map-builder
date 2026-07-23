# Example data sources

The README examples use fixed, local snapshots of public datasets from
[NYC Open Data](https://opendata.cityofnewyork.us/). Builds and tests never fetch
these datasets at runtime.

Snapshot date: **2026-07-24**

## Searchable Lower Manhattan land-use map

- Lot geometry: [TAX_LOT_POLYGON (`i38t-6if2`)](https://data.cityofnewyork.us/d/i38t-6if2),
  published by the New York City Department of Finance
- Land-use and lot attributes:
  [Primary Land Use Tax Lot Output (PLUTO) (`64uk-42ks`)](https://data.cityofnewyork.us/d/64uk-42ks),
  published by the New York City Department of City Planning
- Selection: Manhattan tax lots inside `(-74.015, 40.704, -73.995, 40.7215)`
  with a matching PLUTO record
- Processing: duplicate tax-lot geometry is dissolved by BBL, joined to PLUTO by
  the stable BBL identifier, validated, snapped to seven decimal places, and
  exported in EPSG:4326
- Classification: residential (`01`–`03`), mixed/commercial (`04`–`05`), and
  civic/other (`06`–`11` plus unclassified records)
- Result: 1,699 tax lots: 242 residential, 1,233 mixed/commercial, and
  224 civic/other
- Fields retained: stable BBL-based ID, address, broad and detailed land use,
  zoning district, lot area, building area, built FAR, floors, and year built

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
