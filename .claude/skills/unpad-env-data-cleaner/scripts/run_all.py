"""Orchestrator — run all parsers + validate in one shot.

Usage:
  python run_all.py --out data
  python run_all.py             # outputs to skill's output/
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

PIPELINE = [
    "build_shared",
    "build_meta",
    "parse_pengolahan_sampah",
    "parse_timbulan",
    "parse_water_quality",
    "parse_tree_incidents",
    "parse_traffic_accidents",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full UNPAD env data cleaning pipeline.")
    ap.add_argument("--out", default=None, help="Output dir (default: skill output/)")
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    for step in PIPELINE:
        print(f"\n=== {step} ===")
        cmd = [sys.executable, str(THIS_DIR / f"{step}.py")]
        if args.out:
            cmd.extend(["--out", args.out])
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"[run_all] step {step} failed with code {result.returncode}", file=sys.stderr)
            return result.returncode

    if not args.skip_validate:
        print("\n=== validate ===")
        cmd = [sys.executable, str(THIS_DIR / "validate.py")]
        if args.out:
            cmd.extend(["--data", args.out])
        result = subprocess.run(cmd, check=False)
        return result.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
