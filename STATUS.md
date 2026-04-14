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
- Aggregated OSM point POIs into `data/processed/station_poi_counts_osm_points.csv`
- Aggregated OSM polygon POIs and clipped polygon areas into `data/processed/station_poi_counts_osm_polygons.csv`
- Built a combined OSM station catchment table in `data/processed/station_poi_counts_osm_combined.csv`
- Pulled NOMIS London borough extracts into `nomis_jobs_density_london_boroughs.csv`, `nomis_population_london_boroughs.csv`, and `nomis_population_age_bands_london_boroughs.csv`
- Confirmed the current NOMIS borough pulls work anonymously without storing credentials
- Downloaded London borough boundaries and assigned stations to boroughs
- Built a richer `data/processed/station_feature_table_real.csv` with family/student/affluence proxy improvements
- Rebuilt `data/processed/station_feature_vectors_real.json`
- Added richer context payloads to station vectors for explanation generation
- Added borough/footfall/POI context notes to the real-data demo output
- Added a Streamlit visual layer with a map, ranked table, line ranking chart, and station drilldown
- Added a real-data runnable demo script
- Added `docs/data_sources.md` with access notes and registration requirements

In progress:
- refining borough-level context and explanation quality
- improving proxy quality for affluence and family/student segmentation beyond borough level
- comparing ranked outputs against manual expectations for key station clusters

Next:
- add borough/station context into recommendation explanations
- improve affluence/family/student proxies with more granular public datasets
- compare real-data output against manual expectations for key stations
- decide whether to move from borough-level demographics to smaller-area catchment demographics

Blocking items:
- none currently
