from __future__ import annotations

import csv
import os
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "processed"
BOROUGH_CODES = [
    1778385160, 1778385161, 1778385162, 1778385163, 1778385164, 1778385165,
    1778385166, 1778385167, 1778385168, 1778385169, 1778385170, 1778385171,
    1778385172, 1778385173, 1778385174, 1778385175, 1778385176, 1778385177,
    1778385178, 1778385179, 1778385180, 1778385181, 1778385182, 1778385183,
    1778385184, 1778385185, 1778385186, 1778385187, 1778385188, 1778385189,
    1778385190, 1778385191, 1778385192,
]


def fetch_csv(dataset: str, params: dict[str, str], uid: str) -> list[dict[str, str]]:
    query = dict(params)
    query["uid"] = uid
    url = f"https://www.nomisweb.co.uk/api/v01/dataset/{dataset}.data.csv?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        text = response.read().decode("utf-8", errors="ignore")
    return list(csv.DictReader(StringIO(text)))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    uid = os.environ.get("NOMIS_UID")
    if not uid:
        raise SystemExit("Set NOMIS_UID in the environment before running this script")

    geography = ",".join(str(code) for code in BOROUGH_CODES)

    jobs_density_rows = fetch_csv(
        "NM_57_1",
        {
            "geography": geography,
            "time": "latest",
            "item": "1,3",
            "measures": "20100",
            "select": "date_name,geography_name,geography_code,item_name,obs_value",
        },
        uid,
    )
    write_csv(OUTPUT_DIR / "nomis_jobs_density_london_boroughs.csv", jobs_density_rows)

    population_rows = fetch_csv(
        "NM_31_1",
        {
            "geography": geography,
            "time": "latest",
            "sex": "7",
            "age": "0",
            "measures": "20100",
            "select": "date_name,geography_name,geography_code,age_name,obs_value",
        },
        uid,
    )
    write_csv(OUTPUT_DIR / "nomis_population_london_boroughs.csv", population_rows)

    print("Saved jobs density and population extracts to data/processed/")


if __name__ == "__main__":
    main()
