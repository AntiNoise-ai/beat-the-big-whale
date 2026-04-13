from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "raw" / "london_boroughs.geojson"
URL = "https://opendata.arcgis.com/datasets/0a92a355a8094e0eb20a7a66cf4ca7cf_10.geojson"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        OUTPUT_PATH.write_bytes(response.read())
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
