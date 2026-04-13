from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "data" / "processed" / "station_reference.csv"
COUNTS_PATH = ROOT / "data" / "processed" / "tfl_station_counts_2023.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "station_reference_with_counts.csv"
UNMATCHED_PATH = ROOT / "data" / "processed" / "station_count_unmatched.csv"


ALIASES = {
    "bank": "bankandmonument",
    "balham": "balhamlu",
    "bethnalgreen": "bethnalgreenlu",
    "blackfriars": "blackfriarslu",
    "brixton": "brixtonlu",
    "canarywharf": "canarywharflu",
    "cannonstreet": "cannonstreetlu",
    "charingcross": "charingcrosslu",
    "elephantandcastle": "elephantandcastlelu",
    "euston": "eustonlu",
    "liverpoolstreet": "liverpoolstreetlu",
    "londonbridge": "londonbridgelu",
    "marylebone": "marylebonelu",
    "monument": "bankandmonument",
    "paddington": "paddingtontfl",
    "paddingtonhclineunderground": "paddingtontfl",
    "paddingtonhandclineunderground": "paddingtontfl",
    "shepherdsbushcentral": "shepherdsbushlu",
    "tottenhamhale": "tottenhamhalelu",
    "vauxhall": "vauxhalllu",
    "victoria": "victorialu",
    "waterloo": "waterloolu",
    "westhampstead": "westhampsteadlu",
    "heathrowterminal4": "heathrowterminal4lu",
    "heathrowterminal5": "heathrowterminal5lu",
    "heathrowterminals23": "heathrowterminals123lu",
    "heathrowterminals2and3": "heathrowterminals123lu",
    "edgwareroadbakerloo": "edgwareroadbak",
    "edgwareroadcircleline": "edgwareroaddis",
    "hammersmithdistpiccline": "hammersmithdis",
    "hammersmithdistandpiccline": "hammersmithdis",
    "hammersmithhcline": "hammersmithhandc",
    "hammersmithhandcline": "hammersmithhandc",
}


def normalize(name: str) -> str:
    value = name.lower().strip()
    value = value.replace("&", "and")
    value = value.replace("st.", "st")
    value = value.replace("king's", "kings")
    value = value.replace("shepherd's", "shepherds")
    value = value.replace("(lu)", "lu")
    value = value.replace(" lu", "lu")
    value = value.replace("tfl", "tfl")
    value = re.sub(r"[^a-z0-9]+", "", value)
    return ALIASES.get(value, value)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    reference_rows = load_csv(REFERENCE_PATH)
    counts_rows = load_csv(COUNTS_PATH)

    counts_by_name = {normalize(row["station"]): row for row in counts_rows}
    merged = []
    unmatched = []

    for row in reference_rows:
        key = normalize(row["station_name"])
        count_row = counts_by_name.get(key)
        if count_row:
            merged.append({**row, **count_row})
        else:
            unmatched.append(row)
            merged.append({**row, "annualised_total": ""})

    fieldnames = list(merged[0].keys())
    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)

    with UNMATCHED_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(unmatched[0].keys()) if unmatched else list(reference_rows[0].keys()))
        writer.writeheader()
        writer.writerows(unmatched)

    print(f"Merged {len(reference_rows) - len(unmatched)} of {len(reference_rows)} stations")
    print(f"Unmatched stations: {len(unmatched)}")
    print(f"Saved merged file to {OUTPUT_PATH}")
    print(f"Saved unmatched file to {UNMATCHED_PATH}")


if __name__ == "__main__":
    main()
