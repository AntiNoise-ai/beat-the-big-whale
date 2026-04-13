from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .phase1_config import PROCESSED_DIR


@dataclass(slots=True)
class StationReference:
    station_name: str
    latitude: float
    longitude: float
    zone: str
    lines: list[str]


STATION_REFERENCE_CSV = PROCESSED_DIR / "station_reference.csv"


def load_station_reference(path: Path = STATION_REFERENCE_CSV) -> list[StationReference]:
    if not path.exists():
        return []
    rows: list[StationReference] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                StationReference(
                    station_name=row["station_name"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    zone=row.get("zone", ""),
                    lines=[item.strip() for item in row.get("lines", "").split("|") if item.strip()],
                )
            )
    return rows
