from __future__ import annotations

from copy import deepcopy

BASE_PROFILES = {
    "b2b_tech": {
        "resident_density": 0.4,
        "daytime_workers": 1.4,
        "retail_intensity": 0.3,
        "dining_intensity": 0.6,
        "tourism_intensity": 0.1,
        "office_intensity": 1.5,
        "student_presence": 0.1,
        "family_presence": 0.1,
        "affluence": 0.7,
        "interchange_score": 1.1,
        "footfall_proxy": 1.0,
        "zone_centrality": 1.0
    },
    "luxury_retail": {
        "resident_density": 0.4,
        "daytime_workers": 0.6,
        "retail_intensity": 1.6,
        "dining_intensity": 0.8,
        "tourism_intensity": 1.1,
        "office_intensity": 0.5,
        "student_presence": 0.1,
        "family_presence": 0.2,
        "affluence": 1.5,
        "interchange_score": 0.7,
        "footfall_proxy": 1.2,
        "zone_centrality": 1.2
    },
    "student_food": {
        "resident_density": 0.5,
        "daytime_workers": 0.5,
        "retail_intensity": 0.7,
        "dining_intensity": 1.2,
        "tourism_intensity": 0.2,
        "office_intensity": 0.2,
        "student_presence": 1.8,
        "family_presence": 0.1,
        "affluence": -0.2,
        "interchange_score": 0.8,
        "footfall_proxy": 1.1,
        "zone_centrality": 0.6
    }
}

BUSINESS_PROFILES = tuple(sorted(BASE_PROFILES))


def profile_for(industry: str) -> dict[str, float]:
    if industry not in BASE_PROFILES:
        raise KeyError(f"Unknown industry: {industry}")
    return deepcopy(BASE_PROFILES[industry])
