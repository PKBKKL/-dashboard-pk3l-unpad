"""Validate <out>/*.json against spec invariants without external dependencies.

Checks:
  - Every dataset file is valid JSON with required top-level fields
  - meta.json datasets[].id matches existing files in <out>/
  - Every location_id referenced in datasets exists in shared/locations.json
  - Every regulation_id in water_quality exists in shared/regulations.json
  - Per-dataset invariants (totals, compliance pct sanity, etc.)

Exit code:
  0 = pass
  1 = errors found
  2 = warnings only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import read_json, resolve_output

REQUIRED_FIELDS = {"dataset_id", "version", "generated_at", "source_files", "period", "data_quality_flags"}


def check_meta(out_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    meta_path = out_dir / "meta.json"
    if not meta_path.exists():
        errors.append("meta.json missing")
        return errors, warnings
    meta = read_json(meta_path)
    for ds in meta.get("datasets", []):
        ds_id = ds["id"]
        ds_path = out_dir / f"{ds_id}.json"
        if not ds_path.exists():
            errors.append(f"meta.json references {ds_id}.json but file missing")
    return errors, warnings


def check_dataset_envelope(out_dir: Path, dataset_id: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = out_dir / f"{dataset_id}.json"
    if not path.exists():
        errors.append(f"{dataset_id}.json missing")
        return errors, warnings
    data = read_json(path)
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        errors.append(f"{dataset_id}.json missing fields: {sorted(missing)}")
    if data.get("dataset_id") != dataset_id:
        errors.append(f"{dataset_id}.json has dataset_id={data.get('dataset_id')!r}")
    for f in data.get("data_quality_flags", []):
        if f.get("severity") == "warning":
            warnings.append(f"{dataset_id}: {f.get('message')}")
        elif f.get("severity") == "error":
            errors.append(f"{dataset_id}: {f.get('message')}")
    return errors, warnings


def check_locations(out_dir: Path) -> list[str]:
    errors: list[str] = []
    shared = out_dir / "shared" / "locations.json"
    if not shared.exists():
        errors.append("shared/locations.json missing")
        return errors
    loc_ids = set(read_json(shared)["locations"].keys())

    for ds in ["water_quality", "tree_incidents", "traffic_accidents"]:
        path = out_dir / f"{ds}.json"
        if not path.exists():
            continue
        data = read_json(path)
        for ref in _collect_location_refs(data):
            if ref and ref not in loc_ids:
                errors.append(f"{ds}: location_id {ref!r} not in shared/locations.json")
    return errors


def _collect_location_refs(node) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        if "location_id" in node and isinstance(node["location_id"], str):
            refs.append(node["location_id"])
        for v in node.values():
            refs.extend(_collect_location_refs(v))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_collect_location_refs(item))
    return refs


def check_regulations(out_dir: Path) -> list[str]:
    errors: list[str] = []
    shared = out_dir / "shared" / "regulations.json"
    wq = out_dir / "water_quality.json"
    if not shared.exists() or not wq.exists():
        return errors
    reg_ids = set(read_json(shared)["regulations"].keys())
    data = read_json(wq)
    for r in data.get("reports", []):
        rid = r.get("regulation_id")
        if rid and rid not in reg_ids:
            errors.append(f"water_quality: regulation_id {rid!r} not in shared/regulations.json")
    return errors


def check_pengolahan_invariants(out_dir: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    path = out_dir / "pengolahan_sampah.json"
    if not path.exists():
        return errors, warnings
    data = read_json(path)
    for entry in data.get("daily_entries", []):
        items = entry["items"]
        inc = sum(it["incoming_kg"] for it in items)
        proc = sum(it["processed_kg"] for it in items)
        resid = sum(it["residual_kg"] for it in items)
        for it in items:
            if abs(it["incoming_kg"] - (it["processed_kg"] + it["residual_kg"])) > 0.1:
                warnings.append(f"pengolahan_sampah {entry['date']} {it['category']}: incoming != processed + residual")
        totals = entry["totals"]
        if abs(totals["incoming_kg"] - inc) > 0.1:
            errors.append(f"pengolahan_sampah {entry['date']}: totals.incoming mismatch")
    return errors, warnings


def check_water_quality_summary(out_dir: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    path = out_dir / "water_quality.json"
    if not path.exists():
        return errors, warnings
    data = read_json(path)
    for r in data.get("reports", []):
        ms = r["measurements"]
        compliant = sum(1 for m in ms if m["compliant"] is True)
        non = sum(1 for m in ms if m["compliant"] is False)
        if r["summary"]["compliant_count"] != compliant:
            errors.append(f"water_quality {r['report_no']}: summary.compliant_count mismatch")
        if r["summary"]["non_compliant_count"] != non:
            errors.append(f"water_quality {r['report_no']}: summary.non_compliant_count mismatch")
    return errors, warnings


def check_traffic_yearly(out_dir: Path) -> list[str]:
    warnings: list[str] = []
    path = out_dir / "traffic_accidents.json"
    if not path.exists():
        return warnings
    data = read_json(path)
    for y in data.get("yearly", []):
        for m in y["monthly"]:
            sum_types = sum(m["by_type"].values())
            if sum_types != m["total"]:
                warnings.append(f"traffic_accidents {m['month']}: by_type sum {sum_types} != total {m['total']}")
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate cleaned JSON outputs.")
    ap.add_argument("--data", default=None, help="Path to data dir (default: skill output/)")
    args = ap.parse_args()

    out_dir = resolve_output(args.data)
    if not out_dir.exists():
        print(f"[validate] data dir not found: {out_dir}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    all_warnings: list[str] = []

    e, w = check_meta(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    for ds in ["pengolahan_sampah", "timbulan", "water_quality", "tree_incidents", "traffic_accidents"]:
        e, w = check_dataset_envelope(out_dir, ds)
        all_errors.extend(e); all_warnings.extend(w)

    all_errors.extend(check_locations(out_dir))
    all_errors.extend(check_regulations(out_dir))

    e, w = check_pengolahan_invariants(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    e, w = check_water_quality_summary(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    all_warnings.extend(check_traffic_yearly(out_dir))

    print(f"[validate] errors: {len(all_errors)}, warnings: {len(all_warnings)}")
    for w in all_warnings:
        print(f"  [warn] {w}")
    for e in all_errors:
        print(f"  [err]  {e}", file=sys.stderr)

    if all_errors:
        return 1
    if all_warnings:
        return 2
    print("[validate] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
