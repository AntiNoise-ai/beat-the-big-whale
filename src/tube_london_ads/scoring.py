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


def format_zone(zone: int) -> str:
    return f"Zone {zone}" if zone > 0 else "Outer zone"


def format_millions(value: float | int | None) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return f"{number / 1_000_000:.1f}M"


def build_context_notes(station: StationFeatureVector) -> list[str]:
    context = station.context or {}
    notes = []

    borough_name = context.get("borough_name")
    annualised_total = format_millions(context.get("annualised_total"))
    if borough_name and annualised_total:
        notes.append(f"{format_zone(station.zone)} in {borough_name} with ~{annualised_total} annual entries/exits")
    elif borough_name:
        notes.append(f"{format_zone(station.zone)} in {borough_name}")
    elif annualised_total:
        notes.append(f"{format_zone(station.zone)} with ~{annualised_total} annual entries/exits")

    poi_parts = []
    for key, label in [
        ("total_retail", "retail"),
        ("total_dining", "dining"),
        ("total_office", "office"),
        ("total_tourism", "tourism"),
        ("total_education", "education"),
        ("total_leisure", "leisure"),
    ]:
        value = context.get(key)
        if value is None:
            continue
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError):
            continue
        if number > 0:
            poi_parts.append(f"{number} {label}")
    if poi_parts:
        notes.append(f"~800m catchment includes {', '.join(poi_parts[:4])}")

    borough_context_parts = []
    for key, label in [
        ("borough_children_share", "family-oriented"),
        ("borough_student_age_share", "student-age"),
        ("borough_young_professional_share", "young-professional"),
    ]:
        value = context.get(key)
        try:
            share = float(value)
        except (TypeError, ValueError):
            continue
        if share > 0:
            borough_context_parts.append((share, label))
    if borough_context_parts:
        share, label = max(borough_context_parts, key=lambda item: item[0])
        notes.append(f"Borough demographic skew: {label} ({share * 100:.1f}% of residents)")

    return notes[:2]


def load_station_vectors(path: Path = DATA_PATH) -> list[StationFeatureVector]:
    rows = json.loads(path.read_text())
    return [StationFeatureVector(**row) for row in rows]


# Features that measure "size" rather than audience fit — excluded from value numerator
_REACH_FEATURES = {"footfall_proxy", "zone_centrality"}


def recommend(
    industry: str,
    top_k: int = 5,
    stations: list[StationFeatureVector] | None = None,
    value_mode: bool = False,
) -> RecommendationBundle:
    """Rank stations for an industry profile.

    value_mode=False (default): raw weighted score — rewards large, central stations.
    value_mode=True: audience fit ÷ footfall — surfaces hidden-gem stations that
        match the demographic well but have lower footfall (and thus likely lower
        ad cost and less noise from competing brands).
    """
    weights = profile_for(industry)
    request = BusinessRequest(industry=industry)
    ranked = []
    station_vectors = stations or load_station_vectors()
    for station in station_vectors:
        breakdown = {
            feature: round(station.features[feature] * weights.get(feature, 0.0), 3)
            for feature in station.features
        }
        if value_mode:
            # Audience fit: demographic + POI features only (no footfall/centrality bias)
            audience_fit = sum(
                v for f, v in breakdown.items() if f not in _REACH_FEATURES
            )
            footfall = max(station.features.get("footfall_proxy", 0.1), 0.1)
            score = round(audience_fit / footfall, 3)
        else:
            score = round(sum(breakdown.values()), 3)

        top_reasons = [
            f"{FEATURE_LABELS[name]} ({value:.2f} weighted score)"
            for name, value in sorted(breakdown.items(), key=lambda item: item[1], reverse=True)
            if value > 0 and name not in _REACH_FEATURES
        ][:3]
        ranked.append(
            StationRecommendation(
                station_name=station.station_name,
                score=score,
                lines=station.lines,
                top_reasons=top_reasons,
                feature_breakdown=breakdown,
                context_notes=build_context_notes(station),
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
            "Recommendations are proxy-based, not ROI guarantees.",
            "Feature inputs can come from seed or real public data depending on the caller."
        ]
    )
