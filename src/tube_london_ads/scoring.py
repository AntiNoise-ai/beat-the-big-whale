from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .models import BusinessRequest, RecommendationBundle, StationFeatureVector, StationRecommendation
from .profiles import profile_for

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_stations.json"

FEATURE_LABELS = {
    "resident_density": "strong nearby resident density",
    "daytime_workers": "high daytime worker presence",
    "retail_intensity": "strong retail environment",
    "dining_intensity": "dense dining activity",
    "tourism_intensity": "high tourist activity",
    "office_intensity": "strong office cluster nearby",
    "student_presence": "meaningful student presence",
    "family_presence": "strong family catchment",
    "affluence": "strong affluence proxy",
    "interchange_score": "high interchange value",
    "footfall_proxy": "high footfall proxy",
    "zone_centrality": "high central-London reach"
}


def load_station_vectors(path: Path = DATA_PATH) -> list[StationFeatureVector]:
    rows = json.loads(path.read_text())
    return [StationFeatureVector(**row) for row in rows]


def recommend(
    industry: str,
    top_k: int = 5,
    stations: list[StationFeatureVector] | None = None,
) -> RecommendationBundle:
    weights = profile_for(industry)
    request = BusinessRequest(industry=industry)
    ranked = []
    station_vectors = stations or load_station_vectors()
    for station in station_vectors:
        breakdown = {
            feature: round(station.features[feature] * weights.get(feature, 0.0), 3)
            for feature in station.features
        }
        score = round(sum(breakdown.values()), 3)
        top_reasons = [
            f"{FEATURE_LABELS[name]} ({value:.2f})"
            for name, value in sorted(breakdown.items(), key=lambda item: item[1], reverse=True)
            if value > 0
        ][:3]
        ranked.append(
            StationRecommendation(
                station_name=station.station_name,
                score=score,
                lines=station.lines,
                top_reasons=top_reasons,
                feature_breakdown=breakdown,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    top = ranked[:top_k]
    line_scores = defaultdict(list)
    for station in top:
        for line in station.lines:
            line_scores[line].append(station.score)
    return RecommendationBundle(
        request=request,
        stations=top,
        line_scores={line: round(sum(scores) / len(scores), 3) for line, scores in line_scores.items()},
        notes=[
            "Seed data only.",
            "Phase 1 will replace this with real public-data ingestion."
        ]
    )
