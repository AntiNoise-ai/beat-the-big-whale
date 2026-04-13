from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COUNTS_PATH = ROOT / "data" / "processed" / "station_reference_with_counts.csv"
POI_PATH = ROOT / "data" / "processed" / "station_poi_counts_osm_points.csv"
BOROUGHS_PATH = ROOT / "data" / "processed" / "station_boroughs.csv"
JOBS_PATH = ROOT / "data" / "processed" / "nomis_jobs_density_london_boroughs.csv"
POP_PATH = ROOT / "data" / "processed" / "nomis_population_london_boroughs.csv"
OUTPUT_CSV = ROOT / "data" / "processed" / "station_feature_table_real.csv"
OUTPUT_JSON = ROOT / "data" / "processed" / "station_feature_vectors_real.json"


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


def build_jobs_table() -> pd.DataFrame:
    jobs = pd.read_csv(JOBS_PATH)
    pivot = jobs.pivot_table(index="GEOGRAPHY_NAME", columns="ITEM_NAME", values="OBS_VALUE", aggfunc="first").reset_index()
    pivot.columns.name = None
    return pivot.rename(columns={"GEOGRAPHY_NAME": "borough_name", "Total jobs": "borough_total_jobs", "Jobs density": "borough_jobs_density"})


def build_population_table() -> pd.DataFrame:
    population = pd.read_csv(POP_PATH)
    return population.rename(columns={"GEOGRAPHY_NAME": "borough_name", "OBS_VALUE": "borough_population"})[["borough_name", "borough_population"]]


def main() -> None:
    counts = pd.read_csv(COUNTS_PATH)
    poi = pd.read_csv(POI_PATH)
    boroughs = pd.read_csv(BOROUGHS_PATH)
    jobs = build_jobs_table()
    population = build_population_table()

    merged = counts.merge(poi, on=["station_id", "station_name"], how="left")
    merged = merged.merge(boroughs, on=["station_id", "station_name"], how="left")
    merged = merged.merge(jobs, on="borough_name", how="left")
    merged = merged.merge(population, on="borough_name", how="left")

    for column in ["dining", "education", "healthcare", "office", "retail", "tourism"]:
        if column not in merged:
            merged[column] = 0
        merged[column] = merged[column].fillna(0)

    merged["annualised_total"] = pd.to_numeric(merged["annualised_total"], errors="coerce")
    merged["borough_population"] = pd.to_numeric(merged["borough_population"], errors="coerce")
    merged["borough_hectares"] = pd.to_numeric(merged["borough_hectares"], errors="coerce")
    merged["borough_jobs_density"] = pd.to_numeric(merged["borough_jobs_density"], errors="coerce")
    merged["borough_total_jobs"] = pd.to_numeric(merged["borough_total_jobs"], errors="coerce")

    merged["resident_density_raw"] = merged["borough_population"] / merged["borough_hectares"]
    merged["daytime_workers_raw"] = merged["borough_jobs_density"].fillna(merged["borough_total_jobs"])
    merged["line_count_raw"] = merged["lines"].fillna("").map(lambda value: len([p for p in str(value).split("|") if p]))
    merged["zone_min"] = merged["zone"].map(min_zone)
    merged["zone_centrality_raw"] = 7 - merged["zone_min"].clip(upper=6)

    feature_columns = {
        "resident_density": normalize_0_10(merged["resident_density_raw"].fillna(merged["resident_density_raw"].median())),
        "daytime_workers": normalize_0_10(merged["daytime_workers_raw"].fillna(merged["daytime_workers_raw"].median())),
        "retail_intensity": normalize_0_10(merged["retail"]),
        "dining_intensity": normalize_0_10(merged["dining"]),
        "tourism_intensity": normalize_0_10(merged["tourism"]),
        "office_intensity": normalize_0_10(merged["office"]),
        "student_presence": normalize_0_10(merged["education"]),
        "family_presence": normalize_0_10(merged["resident_density_raw"].fillna(merged["resident_density_raw"].median())),
        "affluence": pd.Series([5.0] * len(merged)),
        "interchange_score": normalize_0_10(merged["line_count_raw"]),
        "footfall_proxy": normalize_0_10(merged["annualised_total"].fillna(merged["annualised_total"].median())),
        "zone_centrality": normalize_0_10(merged["zone_centrality_raw"]),
    }

    for name, values in feature_columns.items():
        merged[name] = values.round(3)

    out_cols = [
        "station_id", "station_name", "borough_name", "zone", "lines", "annualised_total",
        "resident_density", "daytime_workers", "retail_intensity", "dining_intensity",
        "tourism_intensity", "office_intensity", "student_presence", "family_presence",
        "affluence", "interchange_score", "footfall_proxy", "zone_centrality",
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
            }
        )
    OUTPUT_JSON.write_text(json.dumps(vectors, indent=2))
    print(f"Saved {len(merged)} rows to {OUTPUT_CSV}")
    print(f"Saved feature vectors to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
