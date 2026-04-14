from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tube_london_ads.models import StationFeatureVector  # noqa: E402
from tube_london_ads.scoring import recommend  # noqa: E402

DATA_PATH = ROOT / "data" / "processed" / "station_feature_vectors_real.json"


def load_vectors() -> list[StationFeatureVector]:
    rows = json.loads(DATA_PATH.read_text())
    return [StationFeatureVector(**row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    result = recommend(industry=args.industry, top_k=args.top_k, stations=load_vectors())
    print(f"Industry: {result.request.industry}")
    print("Top stations:")
    for idx, station in enumerate(result.stations, start=1):
        print(f"{idx}. {station.station_name} — {station.score:.2f}")
        print(f"   Why: {'; '.join(station.top_reasons)}")
        if station.context_notes:
            print(f"   Context: {'; '.join(station.context_notes)}")
    print("Top lines:")
    for line, score in sorted(result.line_scores.items(), key=lambda item: item[1], reverse=True):
        print(f"- {line}: {score:.2f}")


if __name__ == "__main__":
    main()
