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
- Added `docs/data_sources.md` with access notes and registration requirements

In progress:
- OSM catchment and POI aggregation
- demographic/workplace source selection
- station-level feature engineering from real public inputs

Next:
- aggregate nearby POIs by category
- convert joined station counts into normalized footfall features
- pull initial demographic/workplace proxies from NOMIS
- join public demographic/workplace proxies

Blocking items:
- none yet for transport and OSM layers
- later, a Nomis account may help for larger demographic/workplace pulls
