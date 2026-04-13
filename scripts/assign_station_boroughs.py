from __future__ import annotations

import geopandas as gpd
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIONS_PATH = ROOT / "data" / "processed" / "station_reference.csv"
BOROUGHS_PATH = ROOT / "data" / "raw" / "london_boroughs.geojson"
OUTPUT_PATH = ROOT / "data" / "processed" / "station_boroughs.csv"


def main() -> None:
    stations = pd.read_csv(STATIONS_PATH)
    station_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations["longitude"], stations["latitude"]),
        crs="EPSG:4326",
    )
    boroughs = gpd.read_file(BOROUGHS_PATH)[["BOROUGH", "CODE", "HECTARES", "geometry"]].rename(
        columns={"BOROUGH": "borough_name", "CODE": "borough_code", "HECTARES": "borough_hectares"}
    )
    joined = gpd.sjoin(station_gdf, boroughs, predicate="within", how="left")
    result = joined[[
        "station_id",
        "station_name",
        "borough_name",
        "borough_code",
        "borough_hectares",
    ]].copy()
    result.to_csv(OUTPUT_PATH, index=False)
    unmatched = result["borough_code"].isna().sum()
    print(f"Saved {len(result)} station borough rows to {OUTPUT_PATH}")
    print(f"Unmatched stations: {unmatched}")


if __name__ == "__main__":
    main()
