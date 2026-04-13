from __future__ import annotations

POI_CATEGORY_RULES = {
    "dining": {"amenity": ["restaurant", "cafe", "fast_food", "bar", "pub"]},
    "retail": {"shop": ["mall", "supermarket", "department_store", "clothes", "convenience"]},
    "office": {"office": ["company", "government", "financial", "it"]},
    "tourism": {"tourism": ["attraction", "museum", "gallery", "hotel"]},
    "education": {"amenity": ["university", "college", "school"]},
    "healthcare": {"amenity": ["hospital", "clinic", "doctors", "pharmacy"]},
}
