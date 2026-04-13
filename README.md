# London Tube Advertising Recommender

This folder tracks progress on a public-data-first product for recommending London Underground stations and lines for advertising campaigns.

Goal:
A company enters its business/industry and the product recommends the best stations or lines based on nearby residents, workers, retail, restaurants, tourism, and other public-data proxies.

Current status:
- MVP concept defined
- seed scoring engine built
- Phase 1 started: real public-data ingestion scaffold

Contents:
- `STATUS.md` — concise progress log
- `docs/` — MVP and public-data planning docs
- `src/tube_london_ads/` — starter code for scoring and Phase 1 ingestion
- `data/sample_stations.json` — seed station features used by the current demo
- `scripts/download_public_inputs.py` — starter downloader for public datasets

Quick demo:
```bash
cd london-tube-advertising
python -m src.tube_london_ads.phase1_demo --industry luxury_retail --top-k 5
```

Important:
The current recommendations are strategy proxies, not exact ROI predictions.
