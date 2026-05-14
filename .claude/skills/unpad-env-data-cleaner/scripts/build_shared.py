"""Copy resources/locations_master.json + regulations_master.json into <out>/shared/."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import RESOURCES_DIR, read_json, resolve_output, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Build data/shared/*.json from master resources.")
    ap.add_argument("--out", help="Output dir (default: skill output/)", default=None)
    args = ap.parse_args()

    out_dir = resolve_output(args.out)
    shared_dir = out_dir / "shared"

    locations = read_json(RESOURCES_DIR / "locations_master.json")
    regulations = read_json(RESOURCES_DIR / "regulations_master.json")

    write_json(shared_dir / "locations.json", locations)
    write_json(shared_dir / "regulations.json", regulations)

    print(f"[build_shared] wrote {shared_dir / 'locations.json'} ({len(locations['locations'])} locations)")
    print(f"[build_shared] wrote {shared_dir / 'regulations.json'} ({len(regulations['regulations'])} regulations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
