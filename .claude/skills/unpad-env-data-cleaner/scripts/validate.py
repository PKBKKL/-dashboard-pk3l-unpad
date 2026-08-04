"""Validate <out>/*.json against spec invariants without external dependencies.

Checks:
  - Every dataset file is valid JSON with required top-level fields
  - meta.json datasets[].id matches existing files in <out>/
  - Every location_id referenced in datasets exists in shared/locations.json
  - Every regulation_id in water_quality exists in shared/regulations.json
  - Per-dataset invariants (totals, compliance pct sanity, etc.)
  - ANTI-REGRESI: hasil rebuild tidak boleh memuat lebih sedikit hari, bulan,
    laporan, entri, atau kilogram daripada baseline yang tercatat di _baseline.json

Exit code:
  0 = pass
  1 = errors found (termasuk regresi data)
  2 = warnings only

Baseline:
  python validate.py --data data --update-baseline   # setelah perubahan sah
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import read_json, resolve_output, write_json

REQUIRED_FIELDS = {"dataset_id", "version", "generated_at", "source_files", "period", "data_quality_flags"}
BASELINE_NAME = "_baseline.json"
FLOAT_TOL = 0.001


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


# ── Anti-regresi ─────────────────────────────────────────────────────────
#
# Pipeline menimpa data/*.json seutuhnya. Kalau sebuah file sumber terpotong,
# tertukar dengan versi lama, atau parsernya salah kolom, rebuild akan
# menghasilkan JSON yang lebih miskin TANPA error. Baseline mengunci angka
# minimum yang pernah tercapai; setiap penurunan dianggap error, bukan warning.


def _metrics(out_dir: Path) -> dict:
    """Ukuran cakupan tiap dataset: counts & totals (harus naik atau tetap),
    keys (daftar bulan/tahun/laporan yang tidak boleh hilang)."""
    m: dict[str, dict] = {}

    def add(ds, counts, totals=None, keys=None):
        m[ds] = {"counts": counts, "totals": totals or {}, "keys": keys or {}}

    p = out_dir / "timbulan.json"
    if p.exists():
        d = read_json(p)
        months = [x["month"] for x in d.get("monthly_summary", []) if x.get("total_kg")]
        add("timbulan",
            {"daily_entries": len(d.get("daily_entries", []))},
            {"total_kg": round(sum(e.get("total_kg") or 0 for e in d.get("daily_entries", [])), 3)},
            {"months_with_data": months})

    p = out_dir / "pengolahan_sampah.json"
    if p.exists():
        d = read_json(p)
        add("pengolahan_sampah",
            {"daily_entries": len(d.get("daily_entries", []))},
            {"incoming_kg": round(sum(x.get("incoming_kg") or 0 for x in d.get("monthly_summary", [])), 3)},
            {"months": [x["month"] for x in d.get("monthly_summary", [])]})

    p = out_dir / "water_quality.json"
    if p.exists():
        d = read_json(p)
        add("water_quality",
            {"reports": len(d.get("reports", [])),
             "measurements": sum(len(r.get("measurements", [])) for r in d.get("reports", []))},
            {},
            {"report_no": [r["report_no"] for r in d.get("reports", [])]})

    p = out_dir / "water_quality_ip.json"
    if p.exists():
        d = read_json(p)
        add("water_quality_ip",
            {"points": len(d.get("points", [])),
             "point_years": sum(len(pt.get("years", {})) for pt in d.get("points", []))},
            {},
            {"years": [str(y) for y in d.get("years", [])]})

    p = out_dir / "tree_incidents.json"
    if p.exists():
        d = read_json(p)
        add("tree_incidents",
            {"locations": len(d.get("incidents_by_location", []))},
            {"total_events": d.get("yearly_totals", {}).get("total", 0)})

    p = out_dir / "traffic_accidents.json"
    if p.exists():
        d = read_json(p)
        # spec 1.1 memakai `incidents_detail`; 1.0 memakai `incidents_detail_2026`.
        # Toleransi dua nama agar baseline tetap berlaku selama masa transisi.
        detail = d.get("incidents_detail")
        if detail is None:
            detail = d.get("incidents_detail_2026", [])
        add("traffic_accidents",
            {"incidents_detail": len(detail)},
            {f"total_{y['year']}": y.get("total_yearly_computed", 0) for y in d.get("yearly", [])},
            {"years": [str(y["year"]) for y in d.get("yearly", [])]})

    p = out_dir / "b3_waste.json"
    if p.exists():
        d = read_json(p)
        # Logbook TPS ikut dijaga. Kalau parsernya rusak, catatan limbah keluar
        # akan menyusut — pengaman ini menahannya sebelum promosi.
        tps = d.get("tps_logbook", {}).get("summary", {})
        add("b3_waste",
            {"entries": len(d.get("entries", [])),
             "tps_entri_masuk": tps.get("entri_masuk", 0),
             "tps_entri_keluar": tps.get("entri_keluar", 0),
             "tps_pengiriman": tps.get("pengiriman", 0)},
            {"volume_liter": round(d.get("summary", {}).get("total_volume_liter") or 0, 3),
             "tps_keluar_kg": round(tps.get("total_keluar_kg") or 0, 3)},
            {"months": [x["month"] for x in d.get("monthly_totals", []) if x.get("entries")]})

    p = out_dir / "electricity.json"
    if p.exists():
        d = read_json(p)
        s = d.get("summary", {})
        add("electricity",
            {"months_with_data": s.get("months_with_data", 0),
             "year_count": s.get("year_count", 0)},
            {"total_kwh": round(s.get("total_kwh") or 0, 2)},
            {"months": [x["month"] for x in d.get("monthly", []) if x.get("kwh")]})

    return m


def write_baseline(out_dir: Path) -> Path:
    path = out_dir / BASELINE_NAME
    write_json(path, {
        "note": ("Angka minimum yang pernah tercapai per dataset. validate.py MENOLAK hasil rebuild "
                 "yang lebih kecil dari ini. Perbarui hanya lewat --update-baseline, setelah yakin "
                 "penurunannya memang disengaja."),
        "updated_at": date.today().isoformat(),
        "datasets": _metrics(out_dir),
    })
    return path


def check_no_regression(out_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    base_path = out_dir / BASELINE_NAME
    if not base_path.exists():
        warnings.append(
            f"{BASELINE_NAME} belum ada — pengaman anti-regresi TIDAK aktif. "
            f"Jalankan: python validate.py --data <dir> --update-baseline")
        return errors, warnings

    baseline = read_json(base_path).get("datasets", {})
    current = _metrics(out_dir)

    for ds, base in baseline.items():
        cur = current.get(ds)
        if cur is None:
            errors.append(f"REGRESI {ds}: dataset ada di baseline tapi file-nya hilang dari hasil rebuild")
            continue
        for name, want in base.get("counts", {}).items():
            got = cur["counts"].get(name)
            if got is None:
                errors.append(f"REGRESI {ds}.{name}: metrik hilang dari hasil rebuild")
            elif got < want:
                errors.append(f"REGRESI {ds}.{name}: {got} < baseline {want} (kehilangan {want - got})")
        for name, want in base.get("totals", {}).items():
            got = cur["totals"].get(name)
            if got is None:
                errors.append(f"REGRESI {ds}.{name}: metrik hilang dari hasil rebuild")
            elif got < want - FLOAT_TOL:
                errors.append(f"REGRESI {ds}.{name}: {got:,.3f} < baseline {want:,.3f} (selisih {want - got:,.3f})")
        for name, want_keys in base.get("keys", {}).items():
            got_keys = set(cur["keys"].get(name, []))
            missing = [k for k in want_keys if k not in got_keys]
            if missing:
                errors.append(f"REGRESI {ds}.{name}: hilang {missing}")

    for ds in current:
        if ds not in baseline:
            warnings.append(f"{ds}: belum ada di baseline (dataset baru?) — jalankan --update-baseline bila memang disengaja")

    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate cleaned JSON outputs.")
    ap.add_argument("--data", default=None, help="Path to data dir (default: skill output/)")
    ap.add_argument("--update-baseline", action="store_true",
                    help="Tulis ulang _baseline.json dari isi data dir saat ini, lalu keluar.")
    ap.add_argument("--skip-regression", action="store_true",
                    help="Lewati pengaman anti-regresi (BAHAYA — hanya untuk penurunan data yang disengaja).")
    args = ap.parse_args()

    out_dir = resolve_output(args.data)
    if not out_dir.exists():
        print(f"[validate] data dir not found: {out_dir}", file=sys.stderr)
        return 1

    if args.update_baseline:
        path = write_baseline(out_dir)
        print(f"[validate] baseline diperbarui: {path}")
        for ds, m in _metrics(out_dir).items():
            print(f"  {ds}: {m['counts']} {m['totals']}")
        return 0

    all_errors: list[str] = []
    all_warnings: list[str] = []

    e, w = check_meta(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    for ds in ["pengolahan_sampah", "timbulan", "water_quality", "tree_incidents", "traffic_accidents", "b3_waste", "electricity"]:
        e, w = check_dataset_envelope(out_dir, ds)
        all_errors.extend(e); all_warnings.extend(w)

    all_errors.extend(check_locations(out_dir))
    all_errors.extend(check_regulations(out_dir))

    e, w = check_pengolahan_invariants(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    e, w = check_water_quality_summary(out_dir)
    all_errors.extend(e); all_warnings.extend(w)

    all_warnings.extend(check_traffic_yearly(out_dir))

    if args.skip_regression:
        all_warnings.append("pengaman anti-regresi DILEWATI (--skip-regression)")
    else:
        e, w = check_no_regression(out_dir)
        all_errors.extend(e); all_warnings.extend(w)

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
