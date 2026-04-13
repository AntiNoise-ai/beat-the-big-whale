from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

FEATURE_NAMES = [
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


@dataclass(slots=True)
class StationFeatureVector:
    station_name: str
    lines: List[str]
    zone: int
    features: Dict[str, float]


@dataclass(slots=True)
class BusinessRequest:
    industry: str
    budget: str = "medium"
    emphasis: Dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class StationRecommendation:
    station_name: str
    score: float
    lines: List[str]
    top_reasons: List[str]
    feature_breakdown: Dict[str, float]


@dataclass(slots=True)
class RecommendationBundle:
    request: BusinessRequest
    stations: List[StationRecommendation]
    line_scores: Dict[str, float]
    notes: List[str]
