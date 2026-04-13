from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


@dataclass(frozen=True)
class DownloadTarget:
    name: str
    url: str
    destination: Path
    required: bool = False


DOWNLOAD_TARGETS = [
    DownloadTarget(
        name="tfl-annual-station-counts-2023",
        url="https://crowding.data.tfl.gov.uk/Annual%20Station%20Counts/2023/AC2023_AnnualisedEntryExit.xlsx",
        destination=RAW_DIR / "AC2023_AnnualisedEntryExit.xlsx",
    ),
    DownloadTarget(
        name="geofabrik-greater-london-osm-pbf",
        url="https://download.geofabrik.de/europe/united-kingdom/england/greater-london-latest.osm.pbf",
        destination=RAW_DIR / "greater-london-latest.osm.pbf",
    ),
    DownloadTarget(
        name="geofabrik-greater-london-shapefile",
        url="https://download.geofabrik.de/europe/united-kingdom/england/greater-london-latest-free.shp.zip",
        destination=RAW_DIR / "greater-london-latest-free.shp.zip",
    ),
]
