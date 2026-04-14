from __future__ import annotations

import os
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

os.environ.setdefault("OGR_GEOMETRY_ACCEPT_UNCLOSED_RING", "YES")

ROOT = Path(__file__).resolve().parents[1]
STATIONS_PATH = ROOT / "data" / "processed" / "station_reference.csv"
OSM_PATH = ROOT / "data" / "raw" / "greater-london-latest.osm.pbf"
POINT_OUTPUT_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_points.csv"
POLYGON_OUTPUT_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_polygons.csv"
COMBINED_OUTPUT_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_combined.csv"
BUFFER_METERS = 800
CATEGORIES = ["dining", "education", "healthcare", "office", "retail", "tourism", "leisure"]

CATEGORY_RULES = {
    "dining": {
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "fast_food"),
        ("amenity", "bar"),
        ("amenity", "pub"),
        ("amenity", "food_court"),
    },
    "retail": {
        ("shop", "mall"),
        ("shop", "supermarket"),
        ("shop", "department_store"),
        ("shop", "clothes"),
        ("shop", "convenience"),
        ("shop", "beauty"),
        ("shop", "shoes"),
        ("shop", "jewelry"),
        ("shop", "cosmetics"),
        ("shop", "fashion"),
        ("landuse", "retail"),
        ("building", "retail"),
    },
    "tourism": {
        ("tourism", "attraction"),
        ("tourism", "museum"),
        ("tourism", "gallery"),
        ("tourism", "hotel"),
        ("tourism", "information"),
        ("tourism", "hostel"),
    },
    "office": {
        ("office", "*"),
        ("building", "office"),
        ("building", "commercial"),
        ("landuse", "commercial"),
    },
    "education": {
        ("amenity", "university"),
        ("amenity", "college"),
        ("amenity", "school"),
        ("amenity", "library"),
        ("building", "university"),
        ("building", "college"),
        ("building", "school"),
    },
    "healthcare": {
        ("amenity", "hospital"),
        ("amenity", "clinic"),
        ("amenity", "doctors"),
        ("amenity", "pharmacy"),
        ("amenity", "dentist"),
        ("building", "hospital"),
        ("building", "clinic"),
    },
    "leisure": {
        ("leisure", "park"),
        ("leisure", "garden"),
        ("leisure", "playground"),
        ("leisure", "sports_centre"),
        ("leisure", "stadium"),
        ("leisure", "fitness_centre"),
        ("leisure", "pitch"),
        ("leisure", "recreation_ground"),
        ("amenity", "community_centre"),
        ("amenity", "cinema"),
        ("amenity", "theatre"),
        ("amenity", "arts_centre"),
    },
}

TAG_RE = re.compile(r'"([^"]+)"=>"([^"]+)"')


def parse_tags(value: str | None) -> dict[str, str]:
    if value is None or pd.isna(value) or value == "":
        return {}
    return {key: val for key, val in TAG_RE.findall(str(value))}


def row_to_tags(row: pd.Series) -> dict[str, str]:
    tags = parse_tags(row.get("other_tags"))
    for field in ["amenity", "shop", "tourism", "office", "building", "landuse", "leisure"]:
        value = row.get(field)
        if pd.notna(value) and value not in (None, ""):
            tags[field] = str(value)
    return tags


def matches(tags: dict[str, str], field: str, expected: str) -> bool:
    if expected == "*":
        return bool(tags.get(field))
    return tags.get(field) == expected


def classify(tags: dict[str, str]) -> str | None:
    for category in ["dining", "retail", "tourism", "office", "education", "healthcare", "leisure"]:
        for field, expected in CATEGORY_RULES[category]:
            if matches(tags, field, expected):
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


def load_point_pois() -> gpd.GeoDataFrame:
    gdf = pyogrio.read_dataframe(OSM_PATH, layer="points", where="other_tags IS NOT NULL")
    gdf["tags"] = gdf.apply(row_to_tags, axis=1)
    gdf["category"] = gdf["tags"].map(classify)
    gdf = gdf[gdf["category"].notna()].copy()
    return gdf[["category", "geometry"]].set_crs("EPSG:4326").to_crs("EPSG:27700")


def load_polygon_pois() -> gpd.GeoDataFrame:
    where = (
        "amenity IS NOT NULL OR shop IS NOT NULL OR tourism IS NOT NULL OR office IS NOT NULL "
        "OR building IS NOT NULL OR landuse IS NOT NULL OR leisure IS NOT NULL OR other_tags IS NOT NULL"
    )
    gdf = pyogrio.read_dataframe(OSM_PATH, layer="multipolygons", where=where)
    gdf["tags"] = gdf.apply(row_to_tags, axis=1)
    gdf["category"] = gdf["tags"].map(classify)
    gdf = gdf[gdf["category"].notna()].copy()
    gdf = gdf[["category", "geometry"]].set_crs("EPSG:4326").to_crs("EPSG:27700")
    gdf["polygon_area_m2"] = gdf.geometry.area
    return gdf


def pivot_category_counts(joined: gpd.GeoDataFrame, prefix: str = "") -> pd.DataFrame:
    counts = (
        joined.groupby(["station_id", "station_name", "category"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    counts.columns.name = None
    rename_map = {category: f"{prefix}{category}" for category in CATEGORIES if category in counts.columns}
    counts = counts.rename(columns=rename_map)
    return counts


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = 0
    return df


def main() -> None:
    station_buffers = load_station_buffers()

    point_pois = load_point_pois()
    point_joined = gpd.sjoin(point_pois, station_buffers, predicate="within", how="inner")
    point_counts = ensure_columns(
        pivot_category_counts(point_joined),
        ["station_id", "station_name", *CATEGORIES],
    )
    point_counts = point_counts[["station_id", "station_name", *CATEGORIES]].sort_values(["station_name", "station_id"])
    point_counts.to_csv(POINT_OUTPUT_PATH, index=False)

    polygon_pois = load_polygon_pois()
    polygon_joined = gpd.sjoin(polygon_pois[["category", "geometry"]], station_buffers, predicate="intersects", how="inner")
    polygon_count_wide = ensure_columns(
        pivot_category_counts(polygon_joined, prefix="polygon_"),
        ["station_id", "station_name", *[f"polygon_{category}" for category in CATEGORIES]],
    )
    polygon_count_wide = polygon_count_wide[["station_id", "station_name", *[f"polygon_{category}" for category in CATEGORIES]]]

    polygon_intersections = gpd.overlay(
        polygon_pois[["category", "geometry"]],
        station_buffers,
        how="intersection",
        keep_geom_type=True,
    )
    polygon_intersections["intersection_area_m2"] = polygon_intersections.geometry.area
    polygon_area_wide = (
        polygon_intersections.groupby(["station_id", "station_name", "category"])["intersection_area_m2"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    polygon_area_wide.columns.name = None
    polygon_area_wide = polygon_area_wide.rename(
        columns={category: f"polygon_area_m2_{category}" for category in CATEGORIES if category in polygon_area_wide.columns}
    )
    polygon_area_wide = ensure_columns(
        polygon_area_wide,
        ["station_id", "station_name", *[f"polygon_area_m2_{category}" for category in CATEGORIES]],
    )
    polygon_area_wide = polygon_area_wide[["station_id", "station_name", *[f"polygon_area_m2_{category}" for category in CATEGORIES]]]

    polygon_output = station_buffers[["station_id", "station_name"]].merge(
        polygon_count_wide,
        on=["station_id", "station_name"],
        how="left",
    ).merge(
        polygon_area_wide,
        on=["station_id", "station_name"],
        how="left",
    )
    numeric_polygon_cols = [column for column in polygon_output.columns if column not in {"station_id", "station_name"}]
    polygon_output[numeric_polygon_cols] = polygon_output[numeric_polygon_cols].fillna(0)
    polygon_output = polygon_output.sort_values(["station_name", "station_id"])
    polygon_output.to_csv(POLYGON_OUTPUT_PATH, index=False)

    combined = point_counts.merge(polygon_output, on=["station_id", "station_name"], how="outer")
    for category in CATEGORIES:
        point_column = category
        polygon_column = f"polygon_{category}"
        combined[point_column] = combined[point_column].fillna(0)
        combined[polygon_column] = combined[polygon_column].fillna(0)
        combined[f"total_{category}"] = combined[point_column] + combined[polygon_column]
        combined[f"polygon_area_m2_{category}"] = combined[f"polygon_area_m2_{category}"].fillna(0)
    combined = combined.sort_values(["station_name", "station_id"])
    combined.to_csv(COMBINED_OUTPUT_PATH, index=False)

    print(f"Saved {len(point_counts)} point-based station rows to {POINT_OUTPUT_PATH}")
    print(f"Saved {len(polygon_output)} polygon-based station rows to {POLYGON_OUTPUT_PATH}")
    print(f"Saved {len(combined)} combined station rows to {COMBINED_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
