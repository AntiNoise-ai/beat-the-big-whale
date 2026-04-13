# Status

Updated: 2026-04-13

Done:
- Defined product framing and MVP scope
- Built transparent seed scoring engine
- Added sample major-station dataset
- Started Phase 1 repo scaffold for real public-data ingestion
- Confirmed working public sources for TfL metadata, station counts, and Geofabrik London extracts
- Downloaded raw TfL tube stop-point payload
- Extracted `data/processed/station_reference.csv` with 272 station rows
- Downloaded 2023 annual station counts workbook
- Extracted `data/processed/tfl_station_counts_2023.csv` with 270 LU rows
- Joined station metadata to station counts into `data/processed/station_reference_with_counts.csv`
- Matched 272/272 station rows after normalization/alias handling
- Downloaded the Greater London OSM PBF extract
- Created a local `.venv` with pandas/geopandas/shapely/pyproj/pyogrio
- Aggregated first-pass OSM point-based POI counts into `data/processed/station_poi_counts_osm_points.csv`
- Pulled first NOMIS London borough extracts into `nomis_jobs_density_london_boroughs.csv` and `nomis_population_london_boroughs.csv`
- Added `docs/data_sources.md` with access notes and registration requirements

In progress:
- borough assignment for stations
- station-level feature engineering from real public inputs
- extending OSM aggregation beyond point features

Next:
- map stations to boroughs and join NOMIS borough features
- convert joined station counts into normalized footfall features
- extend OSM aggregation to polygon features and shopping centres/offices
- build first real station feature table for ranking

Blocking items:
- none currently
