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
        "zone_centrality": 1.0,
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
        "zone_centrality": 1.2,
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
        "zone_centrality": 0.6,
    },
    # Consumer tech: tech-savvy, affluent, commuters + students.
    # Wants office clusters, daytime workers, and students; moderate retail/interchange.
    "consumer_tech": {
        "resident_density": 0.5,
        "daytime_workers": 1.3,
        "retail_intensity": 0.7,
        "dining_intensity": 0.5,
        "tourism_intensity": 0.3,
        "office_intensity": 1.4,
        "student_presence": 1.0,
        "family_presence": 0.2,
        "affluence": 1.3,
        "interchange_score": 0.8,
        "footfall_proxy": 1.0,
        "zone_centrality": 0.9,
    },
    # Outdoor lifestyle: active/adventure brands. Tourists, residents, and affluent
    # commuters matter most; moderate retail and daytime workers.
    "outdoor_lifestyle": {
        "resident_density": 1.1,
        "daytime_workers": 0.7,
        "retail_intensity": 0.6,
        "dining_intensity": 0.4,
        "tourism_intensity": 1.4,
        "office_intensity": 0.3,
        "student_presence": 0.4,
        "family_presence": 0.6,
        "affluence": 1.2,
        "interchange_score": 0.7,
        "footfall_proxy": 1.0,
        "zone_centrality": 0.8,
    },
    # Fashion / apparel: high retail + tourism + affluence; daytime footfall.
    # Office density is low priority — targets leisure shoppers, not desk workers.
    "fashion_lifestyle": {
        "resident_density": 0.4,
        "daytime_workers": 1.0,
        "retail_intensity": 1.7,
        "dining_intensity": 0.7,
        "tourism_intensity": 1.3,
        "office_intensity": 0.2,
        "student_presence": 0.5,
        "family_presence": 0.3,
        "affluence": 1.4,
        "interchange_score": 0.8,
        "footfall_proxy": 1.1,
        "zone_centrality": 1.0,
    },
    # Food & beverage: cafes, drinks, FMCG. Dining + daytime workers + students
    # + interchange traffic are the primary drivers.
    "food_beverage": {
        "resident_density": 0.6,
        "daytime_workers": 1.2,
        "retail_intensity": 0.6,
        "dining_intensity": 1.6,
        "tourism_intensity": 0.5,
        "office_intensity": 0.7,
        "student_presence": 1.1,
        "family_presence": 0.4,
        "affluence": 0.5,
        "interchange_score": 1.2,
        "footfall_proxy": 1.0,
        "zone_centrality": 0.7,
    },
    # Financial services / fintech: affluent office workers are the core target.
    # Tourism and student presence are low value for this category.
    "financial_services": {
        "resident_density": 0.4,
        "daytime_workers": 1.5,
        "retail_intensity": 0.3,
        "dining_intensity": 0.4,
        "tourism_intensity": 0.1,
        "office_intensity": 1.6,
        "student_presence": 0.1,
        "family_presence": 0.1,
        "affluence": 1.4,
        "interchange_score": 0.9,
        "footfall_proxy": 1.0,
        "zone_centrality": 1.1,
    },
}

BUSINESS_PROFILES = tuple(sorted(BASE_PROFILES))

# Human-readable labels shown in the UI profile selector
PROFILE_LABELS: dict[str, str] = {
    "b2b_tech": "B2B Tech",
    "consumer_tech": "Consumer Tech (e.g. DJI, Apple, Samsung)",
    "fashion_lifestyle": "Fashion & Lifestyle",
    "financial_services": "Financial Services & Fintech",
    "food_beverage": "Food & Beverage",
    "luxury_retail": "Luxury Retail",
    "outdoor_lifestyle": "Outdoor & Active Lifestyle",
    "student_food": "Student / Budget Food",
}

# Short description for each profile, shown in the brief panel
PROFILE_DESCRIPTIONS: dict[str, str] = {
    "b2b_tech": "Targets office clusters and business districts with high daytime professional traffic.",
    "consumer_tech": "Reaches tech-savvy commuters, affluent workers, and students near office and campus hubs.",
    "fashion_lifestyle": "Optimises for high-footfall retail and tourist destinations frequented by trend-conscious shoppers.",
    "financial_services": "Focuses on affluent office workers in business districts; low tourism/student weighting.",
    "food_beverage": "Prioritises dining-dense, interchange-heavy stations with strong daytime and student traffic.",
    "luxury_retail": "Targets affluent, tourist-heavy, high-retail zones for premium brand exposure.",
    "outdoor_lifestyle": "Seeks high-tourism and resident-density stations near parks and activity corridors.",
    "student_food": "Concentrates on student-heavy catchments with strong dining presence.",
}


def profile_for(industry: str) -> dict[str, float]:
    if industry not in BASE_PROFILES:
        raise KeyError(f"Unknown industry: {industry}")
    return deepcopy(BASE_PROFILES[industry])
