"""Semai buku besar dari data/*.json — dijalankan SEKALI.

JSON dashboard adalah satu-satunya salinan tersisa untuk timbulan Mei–Juni 2026
(208.586 kg) dan kecelakaan Mei–Juni 2026 (6 kasus). Workbook aslinya hilang.
Skrip ini memindahkan isinya ke buku besar teks yang ikut git.

Menolak menimpa buku besar yang sudah ada, kecuali dengan --paksa.

    python seed_ledger.py                 # semai ke data/_ledger/
    python seed_ledger.py --ledger <dir>  # ke folder lain (uji)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ledger import (
    FREEZE_FIELDS,
    PETA_FIELDS,
    fmt,
    ledger_dir,
    today_iso,
    write_md_mirror,
    write_rows,
)
from _utils import find_project_root, read_json

CATEGORY_COLS = ["organik_anorganik", "sisa_makanan", "lingkungan", "aset"]

# Pola header workbook → kategori. Prioritas menentukan pemenang:
# 'SOD RS (Pick Up)' harus jadi sisa_makanan, bukan lingkungan.
PETA_AWAL = [
    (1, "SOD RS", "substring", "sisa_makanan", "", "", "SOD Rumah Sakit"),
    (2, "Tim Angsa", "substring", "organik_anorganik", "", "", "Truk UNPAD"),
    (3, "IPDN", "substring", "ipdn", "", "", "Operator tamu, dipisah dari UNPAD"),
    (4, "Cator", "substring", "sisa_makanan", "", "", "Cator UNPAD (SOD)"),
    (5, "Viar", "substring", "aset", "", "2026-06-30",
     "Sampai Juni 2026 Viar dihitung sebagai aset"),
    (6, "Viar", "substring", "sisa_makanan", "2026-07-01", "",
     "Keputusan pemilik 9 Juli 2026: Viar (SOD) = limbah sisa makanan"),
    (7, "Mobil Traga", "substring", "aset", "", "", "Aset tak terpakai"),
    (8, "Daun & Ranting", "substring", "lingkungan", "", "", ""),
    (9, "Pick Up", "substring", "lingkungan", "", "", "Termasuk 'Pick Up (Seresah)'"),
    (10, "Traga", "substring", "aset", "", "", "Cadangan bila label dipersingkat"),
    (90, "Total", "awalan", "__ABAIKAN__", "", "",
     "Kolom Total tidak dipercaya: Overview Maret 43.160 kg vs total sebenarnya 50.189 kg"),
    (91, "Hari", "exact", "__ABAIKAN__", "", "", "Kolom identitas"),
    (92, "Tanggal", "exact", "__ABAIKAN__", "", "", "Kolom identitas"),
    (93, "Warna", "exact", "__ABAIKAN__", "", "", "Kolom bantu"),
    (94, "Kosong", "exact", "__ABAIKAN__", "", "", "Kolom bantu"),
]

TERKUNCI_AWAL = [
    ("timbulan", "2026-01", "2026-06", "2026-07-10",
     "Sumber asli hilang; JSON dashboard satu-satunya salinan. Keputusan pemilik: angka Jan-Jun tidak boleh berubah saat deploy."),
    ("traffic_accidents", "2025-04", "2026-06", "2026-07-10",
     "Sumber asli hilang; Mei-Juni 2026 (6 kasus) hanya ada di JSON dashboard dan arsip."),
]


def seed_timbulan(led: Path, data: dict) -> int:
    rows = []
    for e in sorted(data["daily_entries"], key=lambda x: x["date"]):
        k = e["by_category_kg"]
        rows.append({
            "tanggal": e["date"],
            "hari": e["day_of_week"],
            **{f"{c}_kg": fmt(k[c]) for c in CATEGORY_COLS},
            "ipdn_kg": fmt(e["ipdn_kg"]),
            "catatan": e.get("note") or "",
            "quality_flag": e.get("quality_flag") or "",
            "sumber": "data/timbulan.json (semai)",
            "dicatat_pada": today_iso(),
        })
    fields = ["tanggal", "hari", *[f"{c}_kg" for c in CATEGORY_COLS], "ipdn_kg",
              "catatan", "quality_flag", "sumber", "dicatat_pada"]
    write_rows(led / "timbulan.csv", fields, rows)

    write_rows(led / "timbulan_kategori.csv", ["id", "label", "color_key", "source"],
               [{k: c.get(k, "") for k in ["id", "label", "color_key", "source"]} for c in data["categories"]])
    write_rows(led / "timbulan_kendaraan.csv", ["id", "label", "operator", "tare_kg", "note"],
               [{k: v.get(k, "") for k in ["id", "label", "operator", "tare_kg", "note"]} for v in data["vehicle_sources"]])
    write_rows(led / "timbulan_tare.csv", ["kontainer", "tare_kg"],
               [{"kontainer": k, "tare_kg": v} for k, v in data["container_tare_kg"].items()])
    write_rows(led / "timbulan_flags.csv", ["severity", "message"],
               [{"severity": f["severity"], "message": f["message"]} for f in data["data_quality_flags"]])

    write_md_mirror(led / "timbulan.csv", led / "timbulan.md", "Buku Besar — Timbulan Sampah",
                    "Nilai turunan (unpad_kg, total_kg) tidak disimpan; parser menghitungnya.")
    return len(rows)


def seed_traffic(led: Path, data: dict) -> tuple[int, int]:
    monthly = []
    for y in data["yearly"]:
        for m in y["monthly"]:
            for jenis, jml in sorted(m["by_type"].items()):
                monthly.append({
                    "tahun": y["year"], "bulan": m["month"], "jenis": jenis, "jumlah": jml,
                    "sumber": "data/traffic_accidents.json (semai)", "dicatat_pada": today_iso(),
                })
    write_rows(led / "traffic_accidents.csv",
               ["tahun", "bulan", "jenis", "jumlah", "sumber", "dicatat_pada"], monthly)

    detail_src = data.get("incidents_detail") or data.get("incidents_detail_2026") or []
    detail = [{
        "tahun": it.get("year", int(str(it["month"])[:4])),
        "no": it["no"],
        "bulan": it["month"],
        "jenis": it["type"],
        "lokasi_id": it["location_id"],
        "lokasi_label": it["location_label_raw"],
        "jumlah": it["count"],
        "catatan": it.get("note", "") or "",
        "sumber": "data/traffic_accidents.json (semai)",
        "dicatat_pada": today_iso(),
    } for it in detail_src]
    write_rows(led / "traffic_accidents_detail.csv",
               ["tahun", "no", "bulan", "jenis", "lokasi_id", "lokasi_label", "jumlah",
                "catatan", "sumber", "dicatat_pada"], detail)

    write_rows(led / "traffic_accidents_jenis.csv", ["id", "label"],
               [{"id": v["id"], "label": v["label"]} for v in data["vehicle_types"]])
    write_rows(led / "traffic_accidents_flags.csv", ["severity", "message"],
               [{"severity": f["severity"], "message": f["message"]} for f in data["data_quality_flags"]])

    write_md_mirror(led / "traffic_accidents.csv", led / "traffic_accidents.md",
                    "Buku Besar — Kecelakaan Lalu Lintas",
                    "Satu baris = satu (tahun, bulan, jenis). Total dihitung parser.")
    return len(monthly), len(detail)


def main() -> int:
    ap = argparse.ArgumentParser(description="Semai buku besar dari data/*.json")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--paksa", action="store_true", help="Timpa buku besar yang sudah ada")
    args = ap.parse_args()

    led = ledger_dir(args.ledger)
    if (led / "timbulan.csv").exists() and not args.paksa:
        print(f"[seed_ledger] {led} sudah berisi buku besar. Menolak menimpa.\n"
              f"  Buku besar bersifat append-only; menyemai ulang membuang riwayat.\n"
              f"  Kalau memang disengaja, tambahkan --paksa.", file=sys.stderr)
        return 1

    data_dir = find_project_root() / "data"
    led.mkdir(parents=True, exist_ok=True)

    n_t = seed_timbulan(led, read_json(data_dir / "timbulan.json"))
    n_m, n_d = seed_traffic(led, read_json(data_dir / "traffic_accidents.json"))

    write_rows(led / "_peta_kolom.csv", PETA_FIELDS,
               [dict(zip(PETA_FIELDS, r)) for r in PETA_AWAL])
    write_rows(led / "_terkunci.csv", FREEZE_FIELDS,
               [dict(zip(FREEZE_FIELDS, r)) for r in TERKUNCI_AWAL])

    print(f"[seed_ledger] {led}")
    print(f"  timbulan.csv                 {n_t} baris harian")
    print(f"  traffic_accidents.csv        {n_m} baris (tahun,bulan,jenis)")
    print(f"  traffic_accidents_detail.csv {n_d} baris lokasi")
    print(f"  _peta_kolom.csv              {len(PETA_AWAL)} pola")
    print(f"  _terkunci.csv                {len(TERKUNCI_AWAL)} periode terkunci")
    return 0


if __name__ == "__main__":
    sys.exit(main())
