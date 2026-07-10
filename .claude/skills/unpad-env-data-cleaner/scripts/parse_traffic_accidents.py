"""PENSIUN — JANGAN DIPAKAI. Lihat parse_traffic_accidents_xlsx.py.

MD sumbernya hanya memuat 4 kasus untuk 2026, sementara dashboard memuat 10
(Mei 3 + Juni 3 tidak ada di MD). Menjalankan skrip ini memundurkan
traffic_accidents.json dan menghapus 6 kasus. Sumber resmi sekarang:
'Kecelakaan Lalu Lintas (MASTER).xlsx'.

Disimpan hanya sebagai rujukan sejarah parsing MD.

──────────────────────────────────────────────────────────────────────────
Parse Kecelakaan Lalu Lintas.md → traffic_accidents.json.

Source has two yearly sections (2025 + 2026) each with:
  - 'Jumlah Kasus per Bulan' table
  - 'Persentase per Bulan' table (ignored — we recompute)
  - 2026 also has 'Berdasarkan Lokasi' subsection with details
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md_parser import find_tables
from _utils import (
    base_dataset,
    find_archived_md,
    find_project_root,
    flag,
    load_md,
    parse_number,
    resolve_output,
    slugify,
    write_json,
)

SOURCE_MD = "Kecelakaan Lalu Lintas.md"
DATASET_ID = "traffic_accidents"

VEHICLE_TYPE_LABEL_TO_ID = {
    "Tunggal Sepeda Motor": "tunggal_motor",
    "Tunggal motor": "tunggal_motor",
    "Tunggal Mobil": "tunggal_mobil",
    "Beam": "beam",
    "Tabrakan antar roda dua": "tabrak_2roda",
    "Antar roda dua": "tabrak_2roda",
    "Tabrakan antar roda dua dan beam": "tabrak_2roda_beam",
    "Tabrakan antar roda dua dan roda empat": "tabrak_2roda_4roda",
    "Tabrakan antar roda empat dan beam": "tabrak_4roda_beam",
    "Beam dan Mobil": "tabrak_4roda_beam",
    "Pejalan kaki": "pejalan_kaki",
}

LOCATION_LABEL_TO_ID = {
    "RSPTN": "rsptn", "FK": "fk", "FKG": "fkg", "FEB": "feb",
    "Pertanian": "faperta", "Faperta": "faperta",
    "Tugu makalangan": "tugu-makalangan", "Tugu Makalangan": "tugu-makalangan",
}


def parse_year_table(md_text: str, year_section_id: str, year: int) -> list[dict]:
    """Parse the 'Jumlah Kasus per Bulan' table under '## Tahun YYYY'."""
    tables = find_tables(md_text, section_contains=year_section_id)
    target_table = None
    for t in tables:
        if any("Jumlah Kasus per Bulan" in s for s in t.section_path):
            target_table = t
            break
    if not target_table:
        return []
    headers = [h.strip() for h in target_table.headers]
    monthly_buckets: dict[str, dict[str, int]] = {}
    for row in target_table.as_dicts():
        jenis_raw = (row.get("Jenis Kecelakaan") or "").strip().replace("**", "").strip()
        if not jenis_raw or jenis_raw.startswith("Total"):
            continue
        type_id = VEHICLE_TYPE_LABEL_TO_ID.get(jenis_raw)
        if not type_id:
            continue
        for h in headers[1:]:
            if h in {"Jenis Kecelakaan"}:
                continue
            val_raw = (row.get(h) or "").strip().replace("**", "").strip()
            if not val_raw:
                continue
            n = parse_number(val_raw)
            if n is None:
                continue
            month_label = h.strip()
            if month_label not in MONTH_NAME_TO_NUM:
                continue
            month_iso = f"{year:04d}-{MONTH_NAME_TO_NUM[month_label]:02d}"
            bucket = monthly_buckets.setdefault(month_iso, {})
            bucket[type_id] = bucket.get(type_id, 0) + int(n)
    return monthly_buckets


MONTH_NAME_TO_NUM = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4, "Mei": 5, "Juni": 6,
    "Juli": 7, "Agustus": 8, "September": 9, "Oktober": 10, "November": 11, "Desember": 12,
}


def build_yearly(monthly_buckets: dict[str, dict[str, int]], year: int) -> dict:
    months = sorted(monthly_buckets.keys())
    rows = []
    total = 0
    for m in months:
        bt = monthly_buckets[m]
        mt = sum(bt.values())
        total += mt
        rows.append({"month": m, "by_type": dict(bt), "total": mt})
    return {"year": year, "monthly": rows, "total_yearly_computed": total}


def parse_detailed_2026(md_text: str) -> list[dict]:
    """Parse the 'Berdasarkan Lokasi > Januari' detail table."""
    tables = find_tables(md_text, section_contains="Berdasarkan Lokasi")
    incidents = []
    for t in tables:
        section = " > ".join(t.section_path)
        if "Januari" not in section:
            continue
        for row in t.as_dicts():
            no = parse_number(row.get("No"))
            jenis_raw = (row.get("Jenis Kecelakaan") or "").strip()
            loc_raw = (row.get("Lokasi") or "").strip()
            count = parse_number(row.get("Jumlah")) or 1
            type_id = VEHICLE_TYPE_LABEL_TO_ID.get(jenis_raw, slugify(jenis_raw))
            loc_id = LOCATION_LABEL_TO_ID.get(loc_raw, slugify(loc_raw))
            note = jenis_raw if type_id == "tabrak_4roda_beam" and "Beam dan Mobil" in jenis_raw else None
            incidents.append({
                "no": int(no) if no else None,
                "month": "2026-01",
                "type": type_id,
                "location_id": loc_id,
                "location_label_raw": loc_raw,
                "count": int(count),
                **({"note": note} if note else {}),
            })
    return incidents


def main() -> int:
    ap = argparse.ArgumentParser(description=f"[PENSIUN] Build {DATASET_ID}.json dari MD lama")
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--i-know-this-is-retired", action="store_true",
                    help="Wajib. Tanpa ini skrip menolak jalan.")
    args = ap.parse_args()

    if not args.i_know_this_is_retired:
        print(
            "[parse_traffic_accidents] SKRIP INI SUDAH PENSIUN dan menolak jalan.\n"
            "  MD sumbernya hanya memuat 4 kasus 2026; dashboard memuat 10.\n"
            "  Menjalankannya menghapus Mei & Juni 2026 (6 kasus).\n"
            "  Pakai:  python parse_traffic_accidents_xlsx.py --out data",
            file=sys.stderr,
        )
        return 1

    project = find_project_root()
    # Dipindahkan ke arsip/ pada 10 Juli 2026; buku besar data/_ledger/
    # traffic_accidents.csv yang kini jadi sumber kebenaran.
    src = Path(args.source) if args.source else find_archived_md(project, SOURCE_MD)
    md_text = load_md(src)

    buckets_2025 = parse_year_table(md_text, "Tahun 2025", 2025)
    buckets_2026 = parse_year_table(md_text, "Tahun 2026", 2026)

    yearly_2025 = build_yearly(buckets_2025, 2025)
    yearly_2026 = build_yearly(buckets_2026, 2026)

    # Reported totals (from source "Total Kasus" row)
    yearly_2025["total_yearly_reported"] = 33
    yearly_2026["total_yearly_reported"] = 4
    yearly_2026["ytd_through_month"] = "2026-04"

    flags = []
    if yearly_2025["total_yearly_computed"] != yearly_2025["total_yearly_reported"]:
        flags.append(flag("warning",
            f"Total Kasus 2025 tercatat {yearly_2025['total_yearly_reported']} di sumber, "
            f"namun penjumlahan baris jenis menghasilkan {yearly_2025['total_yearly_computed']}. "
            "Selisih kemungkinan karena rincian bulanan tidak lengkap di sumber."))
    flags.append(flag("info", "Persentase di sumber dihitung terhadap total tahun (33 untuk 2025). "
                              "Untuk 2026 yang masih parsial, persentase dihitung ulang di frontend berdasarkan total YTD."))

    incidents_2026 = parse_detailed_2026(md_text)

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_MD],
        period={"start": "2025-04-01", "end": "2026-04-30"},
    )
    data["data_quality_flags"] = flags
    data["vehicle_types"] = [
        {"id": "tunggal_motor", "label": "Tunggal Sepeda Motor"},
        {"id": "tunggal_mobil", "label": "Tunggal Mobil"},
        {"id": "beam", "label": "Beam (sepeda listrik)"},
        {"id": "tabrak_2roda", "label": "Tabrakan antar roda dua"},
        {"id": "tabrak_2roda_beam", "label": "Tabrakan roda dua dan Beam"},
        {"id": "tabrak_2roda_4roda", "label": "Tabrakan roda dua dan roda empat"},
        {"id": "tabrak_4roda_beam", "label": "Tabrakan roda empat dan Beam"},
        {"id": "pejalan_kaki", "label": "Pejalan kaki"},
    ]
    data["yearly"] = [yearly_2025, yearly_2026]
    data["incidents_detail_2026"] = incidents_2026

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] wrote {target} (2025: {yearly_2025['total_yearly_computed']} computed, 2026: {yearly_2026['total_yearly_computed']} computed, {len(incidents_2026)} detail records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
