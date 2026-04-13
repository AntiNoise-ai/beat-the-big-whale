from __future__ import annotations

import argparse

from .profiles import BUSINESS_PROFILES
from .scoring import recommend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", required=True, choices=BUSINESS_PROFILES)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    result = recommend(industry=args.industry, top_k=args.top_k)
    print(f"Industry: {result.request.industry}")
    print("Top stations:")
    for idx, station in enumerate(result.stations, start=1):
        print(f"{idx}. {station.station_name} — {station.score:.2f}")
        print(f"   Why: {'; '.join(station.top_reasons)}")
    print("Top lines:")
    for line, score in sorted(result.line_scores.items(), key=lambda item: item[1], reverse=True):
        print(f"- {line}: {score:.2f}")


if __name__ == "__main__":
    main()
