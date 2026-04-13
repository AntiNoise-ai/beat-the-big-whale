from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "AC2023_AnnualisedEntryExit.xlsx"
OUTPUT_PATH = ROOT / "data" / "processed" / "tfl_station_counts_2023.csv"
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def load_shared_strings(archive: ZipFile) -> list[str]:
    shared_xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared = []
    for item in shared_xml.findall("a:si", NS):
        text = "".join(node.text or "" for node in item.iterfind(".//a:t", NS))
        shared.append(text)
    return shared


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    value_node = cell.find("a:v", NS)
    if value_node is None:
        return ""
    if cell.get("t") == "s":
        return shared[int(value_node.text)]
    return value_node.text or ""


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(RAW_PATH) as archive:
        shared = load_shared_strings(archive)
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows = []
    for row in sheet.findall(".//a:sheetData/a:row", NS):
        values = [cell_value(cell, shared) for cell in row.findall("a:c", NS)]
        rows.append(values)

    header = [
        "mode",
        "mnlc",
        "masc",
        "station",
        "coverage",
        "source",
        "entries_monday",
        "entries_midweek",
        "entries_friday",
        "entries_saturday",
        "entries_sunday",
        "exits_monday",
        "exits_midweek",
        "exits_friday",
        "exits_saturday",
        "exits_sunday",
        "weekly_total",
        "twelve_week_total",
        "annualised_total",
    ]
    data_rows = [row[: len(header)] for row in rows[7:] if row and row[0] == "LU"]

    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(data_rows)

    print(f"Saved {len(data_rows)} London Underground rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
