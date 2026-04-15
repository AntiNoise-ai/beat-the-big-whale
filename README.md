# Beat the Big Whale

This repo tracks a public-data-first location-intelligence product for recommending London Underground stations and lines to smaller teams that want sharper ad decisions.

Goal:
A company enters its business/industry and the product recommends the best stations or lines based on nearby residents, workers, retail, restaurants, tourism, and other public-data proxies.

Current status:
- MVP concept defined
- seed scoring engine built
- Phase 1 started: real public-data ingestion scaffold
- real TfL station metadata and station counts ingested
- OSM point + polygon catchment aggregation completed
- NOMIS London borough jobs, population, and age-band extracts completed
- first richer real-data feature table built with improved family/student/affluence proxies
- real-data demo explanations now include borough, footfall, and nearby-POI context
- first visual layer shipped as a Streamlit app with a map, ranked table, and station drilldown
- map upgraded to use TfL Tube line geometries so recommendations sit on a recognizable London network view
- added a classic TfL schematic Tube map reference tab alongside the geographic analysis map

Contents:
- `STATUS.md` — concise progress log
- `docs/` — MVP and public-data planning docs
- `src/tube_london_ads/` — starter code for scoring and Phase 1 ingestion
- `streamlit_app.py` — visual app for exploring ranked stations and lines
- `data/sample_stations.json` — seed station features used by the current demo
- `data/processed/station_reference_with_counts.csv` — joined station metadata + footfall proxy input
- `data/processed/station_poi_counts_osm_points.csv` — OSM point POI counts around stations
- `data/processed/station_poi_counts_osm_polygons.csv` — polygon POI counts and clipped polygon areas around stations
- `data/processed/station_poi_counts_osm_combined.csv` — combined station catchment POI table
- `data/processed/nomis_jobs_density_london_boroughs.csv` — borough-level workplace proxy extract
- `data/processed/nomis_population_age_bands_london_boroughs.csv` — borough-level age-band extract for family/student proxies
- `data/processed/station_feature_table_real.csv` — richer real station-level feature table
- `scripts/download_public_inputs.py` — downloader for public datasets

Quick demo:
```bash
cd london-tube-advertising
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/run_real_data_demo.py --industry luxury_retail --top-k 5
```

Visual app:
```bash
cd london-tube-advertising
. .venv/bin/activate
streamlit run streamlit_app.py
```

Important:
The current recommendations are strategy proxies, not exact ROI predictions.
