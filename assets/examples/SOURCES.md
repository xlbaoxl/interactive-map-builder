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

## Downtown Brooklyn multilayer map

- Polygons: [2020 Neighborhood Tabulation Areas (`9nt8-h7nd`)](https://data.cityofnewyork.us/d/9nt8-h7nd),
  published by the New York City Department of City Planning; four adjoining
  Downtown Brooklyn areas retain their official English names
- Lines: [New York City Bike Routes (`mzxg-pwib`)](https://data.cityofnewyork.us/d/mzxg-pwib),
  published by the New York City Department of Transportation; current Brooklyn
  segments are clipped to the study area, dissolved by street and facility class,
  and the 36 longest grouped routes are retained
- Points: [Subway Entrances and Exits: 2024 (`i9wp-a4ja`)](https://data.ny.gov/d/i9wp-a4ja),
  published by the Metropolitan Transportation Authority; entrances in the study
  area are aggregated into 16 station complexes

## Processing and terms

- All outputs are stored as GeoJSON in EPSG:4326 / CRS84.
- Geometry was validated in EPSG:2263 before reprojection. Coordinates were
  snapped to 7 decimal places with validity-preserving precision reduction.
- Only the display and provenance fields needed by the examples are retained.
- The snapshots are redistributed under the
  [NYC Open Data Terms of Use](https://opendata.cityofnewyork.us/overview/#termsofuse).
- Run `python scripts/prepare_readme_examples.py` from the repository root to
  refresh the snapshots. Review resulting data and counts before committing an
  update because upstream datasets can change.
