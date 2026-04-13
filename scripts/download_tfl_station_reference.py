from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_PATH = RAW_DIR / "tfl_stoppoints_tube.json"
CSV_PATH = PROCESSED_DIR / "station_reference.csv"
BASE_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"


def build_url() -> str:
    params = []
    return BASE_URL if not params else f"{BASE_URL}?{urllib.parse.urlencode(params)}"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def additional_property(item: dict, key: str, default: str = "") -> str:
    for prop in item.get("additionalProperties", []):
        if prop.get("key") == key:
            return prop.get("value", default)
    return default


def extract_station_rows(payload: dict) -> list[dict[str, str]]:
    rows = []
    for item in payload.get("stopPoints", []):
        if item.get("stopType") != "NaptanMetroStation":
            continue
        line_names = sorted({line.get("name", "").strip() for line in item.get("lines", []) if line.get("name")})
        rows.append(
            {
                "station_id": item.get("id", ""),
                "station_name": item.get("commonName", "").replace(" Underground Station", ""),
                "latitude": str(item.get("lat", "")),
                "longitude": str(item.get("lon", "")),
                "zone": additional_property(item, "Zone", ""),
                "lines": "|".join(line_names),
            }
        )
    rows.sort(key=lambda row: row["station_name"])
    return rows


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    payload = fetch_json(build_url())
    RAW_PATH.write_text(json.dumps(payload, indent=2))

    rows = extract_station_rows(payload)
    with CSV_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["station_id", "station_name", "latitude", "longitude", "zone", "lines"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved raw payload to {RAW_PATH}")
    print(f"Saved {len(rows)} station rows to {CSV_PATH}")


if __name__ == "__main__":
    main()
