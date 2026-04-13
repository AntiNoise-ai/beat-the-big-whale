from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tube_london_ads.phase1_config import DOWNLOAD_TARGETS, RAW_DIR  # noqa: E402


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Optional single target name to download")
    args = parser.parse_args()

    targets = [target for target in DOWNLOAD_TARGETS if not args.name or target.name == args.name]
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not targets:
        raise SystemExit("No matching download targets")

    for target in targets:
        print(f"Downloading {target.name} -> {target.destination}")
        download(target.url, target.destination)
        print(f"Saved {target.destination}")


if __name__ == "__main__":
    main()
