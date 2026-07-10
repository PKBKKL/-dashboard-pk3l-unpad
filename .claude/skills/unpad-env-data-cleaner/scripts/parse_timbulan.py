"""PENSIUN — JANGAN DIPAKAI. Lihat parse_timbulan_master.py.

Skrip ini membaca 'Total Timbulan Sampah 2026  (Bulanan).md', yang isinya
tertinggal jauh dari dashboard: hanya Januari–April, dengan angka lama
(Feb 99.644 vs 101.299 di dashboard) dan SKEMA BERBEDA (3 kategori
organik/anorganik_residu/sod, bukan 4 kategori organik_anorganik/sisa_makanan/
lingkungan/aset yang dipakai dashboard).

Menjalankannya akan memundurkan timbulan.json dari 498.818 kg (84 hari,
Jan–Jun) menjadi ~278.518 kg, menghapus Mei & Juni, dan merusak struktur
yang dibaca halaman HTML. Karena itu ia dikeluarkan dari PIPELINE di run_all.py
dan dikunci di main(). Sumber resmi sekarang: 'Timbulan Sampah 2026 (MASTER).xlsx'.

Disimpan hanya sebagai rujukan sejarah parsing MD.

──────────────────────────────────────────────────────────────────────────
Parse Total Timbulan Sampah 2026 (Bulanan).md → timbulan.json.

Reads:
  - Section "Overview" (monthly totals)
  - Per-month sections (Januari..Desember)

Extracts:
  - monthly_summary
  - daily_entries with total_kg, day_of_week, optional category breakdown (April+)
  - detects 'DIPERTANYAKAN' rows → quality_flag

Per-month tables have inconsistent column layouts. We locate the
"Total Timbulan Sampah UNPAD (Kg)" column by header name; categories come from
columns "Organik (Daun + Ranting)" and "Anorganik + Residu" when present.
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
    find_project_root,
    flag,
    load_md,
    parse_number,
    resolve_output,
    round_to,
    write_json,
)

SOURCE_MD = "Total Timbulan Sampah 2026  (Bulanan).md"
DATASET_ID = "timbulan"

MONTHS_ID = [
    ("Januari", "2026-01", 31, ["Januari"]),
    ("Februari", "2026-02", 28, ["Februari"]),
    ("Maret", "2026-03", 31, ["Maret"]),
    ("April", "2026-04", 30, ["April"]),
    ("Mei", "2026-05", 31, ["Mei", "May"]),
    ("Juni", "2026-06", 30, ["Juni", "June"]),
    ("Juli", "2026-07", 31, ["Juli", "July"]),
    ("Agustus", "2026-08", 31, ["Agustus", "August"]),
    ("September", "2026-09", 30, ["September"]),
    ("Oktober", "2026-10", 31, ["Oktober", "October"]),
    ("November", "2026-11", 30, ["November"]),
    ("Desember", "2026-12", 31, ["Desember", "December"]),
]


def parse_overview(md_text: str) -> list[dict]:
    tables = find_tables(md_text, section_contains="Overview")
    if not tables:
        return []
    t = tables[0]
    months = []
    for row in t.as_dicts():
        bulan = (row.get("Bulan") or "").strip()
        if not bulan:
            continue
        total = parse_number(row.get("Total Timbulan (Kg/Bulan)"))
        organik = parse_number(row.get("Organik (Daun dan ranting) (Kg/Bulan)")) or 0
        anorganik_residu = parse_number(row.get("Anorganik + Residu (Kg/Bulan)")) or 0
        sod = parse_number(row.get("SOD (Kg/Bulan)")) or 0
        avg = parse_number(row.get("Rata-Rata (Kg/Hari)"))
        iso = _bulan_to_iso(bulan)
        if iso is None:
            continue
        months.append({
            "month": iso,
            "label": f"{bulan} 2026",
            "total_kg": total,
            "organik_kg": round_to(organik, 2) if organik else 0,
            "anorganik_residu_kg": round_to(anorganik_residu, 2) if anorganik_residu else 0,
            "sod_kg": round_to(sod, 2) if sod else 0,
            "avg_kg_per_calendar_day": round_to(avg, 2) if avg else None,
        })
    return months


def _bulan_to_iso(label: str) -> str | None:
    label_norm = label.strip().lower()
    for _, iso, _, aliases in MONTHS_ID:
        if any(a.lower() == label_norm for a in aliases):
            return iso
    return None


def _days_in_month(iso: str) -> int:
    for _, m, dim, _ in MONTHS_ID:
        if m == iso:
            return dim
    return 30


def parse_monthly_section(md_text: str, aliases: list[str], month_iso: str) -> list[dict]:
    """Extract daily_entries from per-month section. `aliases` covers ID + EN names."""
    real_tables = []
    for alias in aliases:
        tables = find_tables(md_text, section_contains=alias)
        for t in tables:
            if t.section_path and t.section_path[-1].strip().lower() == alias.lower():
                real_tables.append(t)
                break
        if real_tables:
            break
    if not real_tables:
        return []
    t = real_tables[0]

    # Find header names of interest (case-sensitive match)
    total_cols = [h for h in t.headers if "Total Timbulan Sampah UNPAD" in h]
    if not total_cols:
        # Fallback: last numeric column header
        total_cols = [h for h in t.headers if "Total" in h]
    organik_cols = [h for h in t.headers if "Organik (Daun + Ranting)" in h]
    anorganik_cols = [h for h in t.headers if "Anorganik + Residu" in h and "(Kg/Bulan)" not in h]

    # Disambiguate duplicates as the parser appends __2/__3 etc.
    primary_total_header = total_cols[0] if total_cols else None
    primary_organik_header = organik_cols[-1] if organik_cols else None
    primary_anorganik_header = anorganik_cols[-1] if anorganik_cols else None

    entries: list[dict] = []
    for row in t.as_dicts():
        tgl_raw = (row.get("Tanggal") or "").strip()
        if not tgl_raw or not re.match(r"^\d{4}-\d{2}-\d{2}$", tgl_raw):
            continue
        if not tgl_raw.startswith(month_iso):
            continue
        hari = (row.get("Hari") or "").strip()
        total_val = parse_number(row.get(primary_total_header)) if primary_total_header else None
        organik_val = parse_number(row.get(primary_organik_header)) if primary_organik_header else None
        anorganik_val = parse_number(row.get(primary_anorganik_header)) if primary_anorganik_header else None

        # Detect DIPERTANYAKAN
        is_questionable = any("DIPERTANYAKAN" in (v or "") for v in row.values())

        entry = {
            "date": tgl_raw,
            "day_of_week": hari or None,
            "total_kg": total_val if total_val is not None else 0,
            "by_category_kg": None,
            "note": None,
            "quality_flag": None,
        }
        if organik_val is not None or anorganik_val is not None:
            entry["by_category_kg"] = {
                "organik": organik_val if organik_val is not None else 0,
                "anorganik_residu": anorganik_val if anorganik_val is not None else 0,
                "sod": 0,
            }
        if is_questionable:
            entry["note"] = "DIPERTANYAKAN — dikecualikan dari avg"
            entry["quality_flag"] = "excluded_from_average"
            entry["total_kg"] = 0
        entries.append(entry)
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description=f"[PENSIUN] Build {DATASET_ID}.json dari MD lama")
    ap.add_argument("--source", default=None, help=f"Path to {SOURCE_MD}")
    ap.add_argument("--out", default=None)
    ap.add_argument("--i-know-this-is-retired", action="store_true",
                    help="Wajib. Tanpa ini skrip menolak jalan.")
    args = ap.parse_args()

    if not args.i_know_this_is_retired:
        print(
            "[parse_timbulan] SKRIP INI SUDAH PENSIUN dan menolak jalan.\n"
            "  Sumbernya (MD) hanya memuat Januari-April dengan angka lama dan skema 3-kategori.\n"
            "  Menjalankannya akan menghapus Mei & Juni 2026 (208.586 kg) dari dashboard.\n"
            "  Pakai:  python parse_timbulan_master.py --out data\n"
            "  Kalau benar-benar perlu (mis. riset arsip), tambahkan --i-know-this-is-retired\n"
            "  dan JANGAN arahkan --out ke data/.",
            file=sys.stderr,
        )
        return 1

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_MD
    md_text = load_md(src)

    overview = parse_overview(md_text)

    # Collect daily entries from each month section
    daily: list[dict] = []
    for _name, iso, _dim, aliases in MONTHS_ID:
        daily.extend(parse_monthly_section(md_text, aliases, iso))

    # Compute days_active and avg per active day per month
    monthly_summary: list[dict] = []
    for m in overview:
        month_iso = m["month"]
        in_month = [e for e in daily if e["date"].startswith(month_iso)]
        days_active = sum(1 for e in in_month if e["total_kg"] and e["total_kg"] > 0 and e["quality_flag"] != "excluded_from_average")
        days_in_month = _days_in_month(month_iso)
        total = m["total_kg"] or 0
        avg_active = round_to(total / days_active, 2) if days_active else None
        avg_calendar = round_to(total / days_in_month, 2) if days_in_month else None
        category_breakdown = any(e["by_category_kg"] for e in in_month)
        monthly_summary.append({
            **m,
            "days_active": days_active,
            "days_in_month": days_in_month,
            "avg_kg_per_active_day": avg_active,
            "avg_kg_per_calendar_day": avg_calendar,
            "category_breakdown_available": category_breakdown,
        })

    flags = [
        flag("info", "Januari 2026 hanya tercatat 6 hari kerja (26-31 Jan). Rata-rata per hari aktif jauh lebih representatif daripada rata-rata per hari kalender."),
        flag("warning", "April 2026 tanggal 27 ditandai 'DIPERTANYAKAN' di sumber, dikecualikan dari kalkulasi rata-rata aktif."),
        flag("warning", "Februari (99.644 kg) dan April (120.544 kg) jauh di atas Maret (43.160 kg). Perlu konfirmasi apakah ini lonjakan riil atau bias pencatatan."),
        flag("info", "Pemisahan kategori Organik vs Anorganik+Residu baru rapi mulai April 2026; bulan sebelumnya hanya total."),
    ]

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_MD],
        period={"start": "2026-01-26", "end": "2026-04-30"},
    )
    data["unit_default"] = "kg"
    data["data_quality_flags"] = flags
    data["vehicle_sources"] = [
        {"id": "truk-tim-angsa", "label": "Truk UNPAD (Tim Angsa)", "operator": "UNPAD", "tare_kg": None},
        {"id": "truk-ipdn", "label": "Truk IPDN", "operator": "IPDN", "tare_kg": None},
        {"id": "pickup-unpad", "label": "Pick Up UNPAD", "operator": "UNPAD", "tare_kg": 1288},
        {"id": "viar", "label": "Viar", "operator": "UNPAD", "tare_kg": 263},
        {"id": "cator-unpad", "label": "Cator UNPAD", "operator": "UNPAD", "tare_kg": None},
        {"id": "mobil-traga", "label": "Mobil Traga", "operator": "UNPAD", "tare_kg": 1720, "note": "Aset yang tidak terpakai"},
        {"id": "sod-rs", "label": "SOD Rumah Sakit", "operator": "RS UNPAD", "tare_kg": None},
    ]
    data["container_tare_kg"] = {"biru": 3870, "hijau": 3380, "putih": 4190}
    data["categories"] = [
        {"id": "organik", "label": "Organik (Daun + Ranting)", "color_key": "organik"},
        {"id": "anorganik_residu", "label": "Anorganik + Residu", "color_key": "anorganik"},
        {"id": "sod", "label": "SOD (Sampah Olahan/RS)", "color_key": "residu"},
    ]
    data["monthly_summary"] = monthly_summary
    data["daily_entries"] = daily

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] wrote {target} ({len(daily)} daily entries, {len(monthly_summary)} months, {len(flags)} flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
