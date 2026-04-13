from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
import pyogrio

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIONS_PATH = ROOT / "data" / "processed" / "station_reference.csv"
OSM_PATH = ROOT / "data" / "raw" / "greater-london-latest.osm.pbf"
OUTPUT_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_points.csv"
BUFFER_METERS = 800

CATEGORY_MAP = {
    "dining": {
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "fast_food"),
        ("amenity", "bar"),
        ("amenity", "pub"),
    },
    "retail": {
        ("shop", "mall"),
        ("shop", "supermarket"),
        ("shop", "department_store"),
        ("shop", "clothes"),
        ("shop", "convenience"),
        ("shop", "beauty"),
    },
    "tourism": {
        ("tourism", "attraction"),
        ("tourism", "museum"),
        ("tourism", "gallery"),
        ("tourism", "hotel"),
        ("tourism", "information"),
    },
    "office": {
        ("office", "company"),
        ("office", "government"),
        ("office", "financial"),
        ("office", "it"),
        ("office", "coworking"),
    },
    "education": {
        ("amenity", "university"),
        ("amenity", "college"),
        ("amenity", "school"),
    },
    "healthcare": {
        ("amenity", "hospital"),
        ("amenity", "clinic"),
        ("amenity", "doctors"),
        ("amenity", "pharmacy"),
    },
}

TAG_RE = re.compile(r'"([^"]+)"=>"([^"]+)"')


def parse_tags(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    return {key: val for key, val in TAG_RE.findall(value)}


def classify(tags: dict[str, str]) -> str | None:
    for category, pairs in CATEGORY_MAP.items():
        for pair in pairs:
            if tags.get(pair[0]) == pair[1]:
                return category
    return None


def load_station_buffers() -> gpd.GeoDataFrame:
    df = pd.read_csv(STATIONS_PATH)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")
    gdf["geometry"] = gdf.geometry.buffer(BUFFER_METERS)
    return gdf[["station_id", "station_name", "geometry"]]


def load_poi_points() -> gpd.GeoDataFrame:
    where = (
        'other_tags IS NOT NULL AND ('
        'other_tags LIKE \'%"amenity"=>%\' OR '
        'other_tags LIKE \'%"shop"=>%\' OR '
        'other_tags LIKE \'%"tourism"=>%\' OR '
        'other_tags LIKE \'%"office"=>%\''
        ')'
    )
    gdf = pyogrio.read_dataframe(OSM_PATH, layer="points", where=where)
    gdf["tags"] = gdf["other_tags"].map(parse_tags)
    gdf["category"] = gdf["tags"].map(classify)
    gdf = gdf[gdf["category"].notna()].copy()
    return gdf[["category", "geometry"]].set_crs("EPSG:4326").to_crs("EPSG:27700")


def main() -> None:
    station_buffers = load_station_buffers()
    poi_points = load_poi_points()

    joined = gpd.sjoin(
        poi_points,
        station_buffers,
        predicate="within",
        how="inner",
    )
    counts = (
        joined.groupby(["station_id", "station_name", "category"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    counts.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(counts)} station POI rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
