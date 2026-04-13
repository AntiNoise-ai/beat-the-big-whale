# London Tube Advertising Recommender

This folder tracks progress on a public-data-first product for recommending London Underground stations and lines for advertising campaigns.

Goal:
A company enters its business/industry and the product recommends the best stations or lines based on nearby residents, workers, retail, restaurants, tourism, and other public-data proxies.

Current status:
- MVP concept defined
- seed scoring engine built
- Phase 1 started: real public-data ingestion scaffold
- real TfL station metadata and station counts ingested
- initial OSM point-based POI aggregation completed
- initial NOMIS London borough extracts completed

Contents:
- `STATUS.md` — concise progress log
- `docs/` — MVP and public-data planning docs
- `src/tube_london_ads/` — starter code for scoring and Phase 1 ingestion
- `data/sample_stations.json` — seed station features used by the current demo
- `data/processed/station_reference_with_counts.csv` — joined station metadata + footfall proxy input
- `data/processed/station_poi_counts_osm_points.csv` — initial OSM POI counts around stations
- `data/processed/nomis_jobs_density_london_boroughs.csv` — first workplace proxy extract
- `scripts/download_public_inputs.py` — downloader for public datasets

Quick demo:
```bash
cd london-tube-advertising
python -m src.tube_london_ads.phase1_demo --industry luxury_retail --top-k 5
```

Important:
The current recommendations are strategy proxies, not exact ROI predictions.
