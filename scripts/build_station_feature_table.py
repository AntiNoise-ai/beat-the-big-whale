from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COUNTS_PATH = ROOT / "data" / "processed" / "station_reference_with_counts.csv"
POI_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_combined.csv"
BOROUGHS_PATH = ROOT / "data" / "processed" / "station_boroughs.csv"
JOBS_PATH = ROOT / "data" / "processed" / "nomis_jobs_density_london_boroughs.csv"
POP_PATH = ROOT / "data" / "processed" / "nomis_population_london_boroughs.csv"
AGE_BANDS_PATH = ROOT / "data" / "processed" / "nomis_population_age_bands_london_boroughs.csv"
OUTPUT_CSV = ROOT / "data" / "processed" / "station_feature_table_real.csv"
OUTPUT_JSON = ROOT / "data" / "processed" / "station_feature_vectors_real.json"
POI_CATEGORIES = ["dining", "education", "healthcare", "office", "retail", "tourism", "leisure"]


def normalize_0_10(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    min_value = series.min()
    max_value = series.max()
    if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
        return pd.Series([5.0] * len(series), index=series.index)
    return ((series - min_value) / (max_value - min_value) * 10).round(3)


def min_zone(value: str) -> int:
    if pd.isna(value):
        return 6
    parts = [int(part) for part in str(value).replace("+", " ").split() if part.isdigit()]
    return min(parts) if parts else 6


def borough_key(value: str | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    normalized = normalized.replace("&", "and")
    normalized = normalized.replace("city of westminster", "westminster")
    normalized = " ".join(normalized.split())
    return normalized


def build_jobs_table() -> pd.DataFrame:
    jobs = pd.read_csv(JOBS_PATH)
    pivot = jobs.pivot_table(index=["GEOGRAPHY_NAME", "GEOGRAPHY_CODE"], columns="ITEM_NAME", values="OBS_VALUE", aggfunc="first").reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(
        columns={
            "GEOGRAPHY_NAME": "borough_name_nomis",
            "GEOGRAPHY_CODE": "borough_geography_code",
            "Total jobs": "borough_total_jobs",
            "Jobs density": "borough_jobs_density",
        }
    )
    pivot["borough_key"] = pivot["borough_name_nomis"].map(borough_key)
    return pivot


def build_population_table() -> pd.DataFrame:
    population = pd.read_csv(POP_PATH).rename(
        columns={
            "GEOGRAPHY_NAME": "borough_name_nomis",
            "GEOGRAPHY_CODE": "borough_geography_code",
            "OBS_VALUE": "borough_population",
        }
    )
    population["borough_key"] = population["borough_name_nomis"].map(borough_key)
    return population[["borough_key", "borough_population"]]


def build_age_band_table() -> pd.DataFrame:
    age_bands = pd.read_csv(AGE_BANDS_PATH)
    age_bands["borough_key"] = age_bands["GEOGRAPHY_NAME"].map(borough_key)
    age_bands["OBS_VALUE"] = pd.to_numeric(age_bands["OBS_VALUE"], errors="coerce").fillna(0)

    def classify_age_band(age_name: str) -> str | None:
        if age_name in {"Aged under 1 year", "Aged 1 - 4 years", "Aged 5 - 9 years", "Aged 10 - 14 years"}:
            return "children"
        if age_name in {"Aged 15 - 19 years", "Aged 20 - 24 years"}:
            return "student_age"
        if age_name in {"Aged 25 - 29 years", "Aged 30 - 34 years"}:
            return "young_professional"
        return None

    age_bands["age_group"] = age_bands["AGE_NAME"].map(classify_age_band)
    grouped = (
        age_bands[age_bands["age_group"].notna()]
        .groupby(["borough_key", "age_group"])["OBS_VALUE"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    population = build_population_table()
    grouped = grouped.merge(population, on="borough_key", how="left")
    for group in ["children", "student_age", "young_professional"]:
        if group not in grouped:
            grouped[group] = 0
        grouped[f"borough_{group}_share"] = grouped[group] / grouped["borough_population"]
    return grouped[
        [
            "borough_key",
            "children",
            "student_age",
            "young_professional",
            "borough_children_share",
            "borough_student_age_share",
            "borough_young_professional_share",
        ]
    ]


def poi_signal(df: pd.DataFrame, category: str, area_weight: float = 0.35) -> pd.Series:
    total_count = pd.to_numeric(df.get(f"total_{category}", 0), errors="coerce").fillna(0)
    area_m2 = pd.to_numeric(df.get(f"polygon_area_m2_{category}", 0), errors="coerce").fillna(0)
    return total_count.map(math.log1p) + area_m2.div(1000).map(math.log1p) * area_weight


def main() -> None:
    counts = pd.read_csv(COUNTS_PATH)
    poi = pd.read_csv(POI_PATH)
    boroughs = pd.read_csv(BOROUGHS_PATH)
    jobs = build_jobs_table()
    population = build_population_table()
    age_bands = build_age_band_table()

    boroughs["borough_key"] = boroughs["borough_name"].map(borough_key)

    merged = counts.merge(poi, on=["station_id", "station_name"], how="left")
    merged = merged.merge(boroughs, on=["station_id", "station_name"], how="left")
    merged = merged.merge(jobs[["borough_key", "borough_total_jobs", "borough_jobs_density"]], on="borough_key", how="left")
    merged = merged.merge(population, on="borough_key", how="left")
    merged = merged.merge(age_bands, on="borough_key", how="left")

    for category in POI_CATEGORIES:
        for column in [category, f"polygon_{category}", f"total_{category}", f"polygon_area_m2_{category}"]:
            if column not in merged:
                merged[column] = 0
            merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)

    numeric_columns = [
        "annualised_total",
        "borough_population",
        "borough_hectares",
        "borough_jobs_density",
        "borough_total_jobs",
        "borough_children_share",
        "borough_student_age_share",
        "borough_young_professional_share",
    ]
    for column in numeric_columns:
        if column not in merged:
            merged[column] = pd.NA
        merged[column] = pd.to_numeric(merged[column], errors="coerce")

    merged["resident_density_raw"] = merged["borough_population"] / merged["borough_hectares"]
    merged["daytime_workers_raw"] = merged["borough_jobs_density"].fillna(merged["borough_total_jobs"])
    merged["line_count_raw"] = merged["lines"].fillna("").map(lambda value: len([p for p in str(value).split("|") if p]))
    merged["zone_min"] = merged["zone"].map(min_zone)
    merged["zone_centrality_raw"] = 7 - merged["zone_min"].clip(upper=6)
    merged["footfall_proxy_raw"] = merged["annualised_total"].fillna(merged["annualised_total"].median()).map(math.log1p)
    merged["retail_signal_raw"] = poi_signal(merged, "retail")
    merged["dining_signal_raw"] = poi_signal(merged, "dining")
    merged["tourism_signal_raw"] = poi_signal(merged, "tourism")
    merged["office_signal_raw"] = poi_signal(merged, "office")
    merged["education_signal_raw"] = poi_signal(merged, "education")
    merged["leisure_signal_raw"] = poi_signal(merged, "leisure", area_weight=0.2)
    merged["children_share_raw"] = merged["borough_children_share"].fillna(merged["borough_children_share"].median())
    merged["student_age_share_raw"] = merged["borough_student_age_share"].fillna(merged["borough_student_age_share"].median())
    merged["young_professional_share_raw"] = merged["borough_young_professional_share"].fillna(merged["borough_young_professional_share"].median())

    merged["student_presence_raw"] = (
        merged["education_signal_raw"]
        + merged["student_age_share_raw"] * 18
        + merged["young_professional_share_raw"] * 6
    )
    merged["family_presence_raw"] = merged["leisure_signal_raw"] + merged["children_share_raw"] * 25
    merged["affluence_raw"] = (
        merged["retail_signal_raw"]
        + merged["tourism_signal_raw"] * 0.4
        + merged["daytime_workers_raw"].fillna(merged["daytime_workers_raw"].median()).map(math.log1p) * 0.8
        + merged["young_professional_share_raw"] * 25
    )

    feature_columns = {
        "resident_density": normalize_0_10(merged["resident_density_raw"].fillna(merged["resident_density_raw"].median())),
        "daytime_workers": normalize_0_10(merged["daytime_workers_raw"].fillna(merged["daytime_workers_raw"].median()).map(math.log1p)),
        "retail_intensity": normalize_0_10(merged["retail_signal_raw"]),
        "dining_intensity": normalize_0_10(merged["dining_signal_raw"]),
        "tourism_intensity": normalize_0_10(merged["tourism_signal_raw"]),
        "office_intensity": normalize_0_10(merged["office_signal_raw"]),
        "student_presence": normalize_0_10(merged["student_presence_raw"]),
        "family_presence": normalize_0_10(merged["family_presence_raw"]),
        "affluence": normalize_0_10(merged["affluence_raw"]),
        "interchange_score": normalize_0_10(merged["line_count_raw"]),
        "footfall_proxy": normalize_0_10(merged["footfall_proxy_raw"]),
        "zone_centrality": normalize_0_10(merged["zone_centrality_raw"]),
    }

    for name, values in feature_columns.items():
        merged[name] = values.round(3)

    out_cols = [
        "station_id",
        "station_name",
        "borough_name",
        "zone",
        "lines",
        "annualised_total",
        "borough_population",
        "borough_total_jobs",
        "borough_children_share",
        "borough_student_age_share",
        "borough_young_professional_share",
        "total_retail",
        "total_dining",
        "total_tourism",
        "total_office",
        "total_education",
        "total_leisure",
        "resident_density",
        "daytime_workers",
        "retail_intensity",
        "dining_intensity",
        "tourism_intensity",
        "office_intensity",
        "student_presence",
        "family_presence",
        "affluence",
        "interchange_score",
        "footfall_proxy",
        "zone_centrality",
    ]
    merged[out_cols].to_csv(OUTPUT_CSV, index=False)

    vectors = []
    for _, row in merged.iterrows():
        vectors.append(
            {
                "station_name": row["station_name"],
                "lines": [part for part in str(row["lines"]).split("|") if part],
                "zone": min_zone(row["zone"]),
                "features": {
                    "resident_density": float(row["resident_density"]),
                    "daytime_workers": float(row["daytime_workers"]),
                    "retail_intensity": float(row["retail_intensity"]),
                    "dining_intensity": float(row["dining_intensity"]),
                    "tourism_intensity": float(row["tourism_intensity"]),
                    "office_intensity": float(row["office_intensity"]),
                    "student_presence": float(row["student_presence"]),
                    "family_presence": float(row["family_presence"]),
                    "affluence": float(row["affluence"]),
                    "interchange_score": float(row["interchange_score"]),
                    "footfall_proxy": float(row["footfall_proxy"]),
                    "zone_centrality": float(row["zone_centrality"]),
                },
                "context": {
                    "borough_name": None if pd.isna(row["borough_name"]) else row["borough_name"],
                    "annualised_total": None if pd.isna(row["annualised_total"]) else float(row["annualised_total"]),
                    "borough_children_share": None if pd.isna(row["borough_children_share"]) else float(row["borough_children_share"]),
                    "borough_student_age_share": None if pd.isna(row["borough_student_age_share"]) else float(row["borough_student_age_share"]),
                    "borough_young_professional_share": None if pd.isna(row["borough_young_professional_share"]) else float(row["borough_young_professional_share"]),
                    "total_retail": None if pd.isna(row["total_retail"]) else float(row["total_retail"]),
                    "total_dining": None if pd.isna(row["total_dining"]) else float(row["total_dining"]),
                    "total_tourism": None if pd.isna(row["total_tourism"]) else float(row["total_tourism"]),
                    "total_office": None if pd.isna(row["total_office"]) else float(row["total_office"]),
                    "total_education": None if pd.isna(row["total_education"]) else float(row["total_education"]),
                    "total_leisure": None if pd.isna(row["total_leisure"]) else float(row["total_leisure"]),
                },
            }
        )
    OUTPUT_JSON.write_text(json.dumps(vectors, indent=2))
    print(f"Saved {len(merged)} rows to {OUTPUT_CSV}")
    print(f"Saved feature vectors to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
