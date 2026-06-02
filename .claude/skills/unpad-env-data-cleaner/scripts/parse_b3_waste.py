"""Parse Logbook Limbah B3.xlsx → b3_waste.json.

Source: 12 sheets covering Sep 2024 – 2026.
- 10 monthly report sheets ('Laporan Limbah B3 (Sep 2024)' … '(Des. 2025)')
  with columns: No | Nama Lembaga | Nama Limbah | Volume | Satuan | Kode Limbah | Kategori
- 1 combined 2026 sheet adds: Bulan | Tanggal columns
- 1 wide Logbook (TPS Masuk/Keluar/Sisa) — skipped here, different structure

Output: dashboard-ready aggregations (by month, by lembaga, by kode limbah)
plus full entry list for client-side filtering.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import (
    base_dataset,
    find_project_root,
    flag,
    parse_number,
    resolve_output,
    round_to,
    write_json,
)

SOURCE_XLSX = "Logbook Limbah B3.xlsx"
DATASET_ID = "b3_waste"

MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
MONTH_ALIAS_TO_NUM = {}
for i, m in enumerate(MONTHS_ID, start=1):
    MONTH_ALIAS_TO_NUM[m.lower()] = i
    MONTH_ALIAS_TO_NUM[m[:3].lower()] = i
MONTH_ALIAS_TO_NUM.update({"sept": 9, "okt": 10, "des": 12, "agu": 8, "jun": 6, "mei": 5, "feb": 2})


def month_from_sheet(name: str) -> str | None:
    """Extract YYYY-MM from sheet name like 'Laporan Limbah B3 (Sep 2024)'."""
    m = re.search(r"\(([\w\.\s]+)\s+(\d{4})\)", name)
    if not m:
        return None
    token, year = m.group(1).strip().rstrip("."), int(m.group(2))
    num = MONTH_ALIAS_TO_NUM.get(token.lower())
    if num is None:
        return None
    return f"{year:04d}-{num:02d}"


def month_label(iso: str) -> str:
    """2024-09 → 'September 2024'."""
    try:
        y, m = iso.split("-")
        return f"{MONTHS_ID[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def parse_month_from_string(s: str, default_year: int) -> str | None:
    """Parse 'Januari' → '{year}-01'."""
    if not s:
        return None
    num = MONTH_ALIAS_TO_NUM.get(s.strip().lower())
    if num is None:
        return None
    return f"{default_year:04d}-{num:02d}"


def fmt_date(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v).strip() or None


def parse_monthly_sheet(ws, month_iso: str) -> list[dict]:
    """Parse standard 7-col monthly sheet → entries list."""
    entries: list[dict] = []
    # Find header row (has 'No' in col 1)
    header_row = None
    for r in range(1, min(ws.max_row, 10) + 1):
        v0 = ws.cell(row=r, column=1).value
        if v0 and str(v0).strip().lower() in ("no", "no."):
            header_row = r
            break
    if header_row is None:
        return entries
    for r in range(header_row + 1, ws.max_row + 1):
        lembaga = ws.cell(row=r, column=2).value
        limbah = ws.cell(row=r, column=3).value
        if not lembaga or not limbah:
            continue
        volume = parse_number(ws.cell(row=r, column=4).value)
        satuan = ws.cell(row=r, column=5).value
        kode = ws.cell(row=r, column=6).value
        kategori = ws.cell(row=r, column=7).value
        if volume is None:
            continue
        entries.append({
            "month": month_iso,
            "date": None,
            "lembaga": str(lembaga).strip(),
            "limbah": str(limbah).strip(),
            "volume": round_to(float(volume), 3),
            "satuan": (str(satuan).strip() if satuan else ""),
            "kode_limbah": (str(kode).strip() if kode else ""),
            "kategori": (str(kategori).strip() if kategori else ""),
        })
    return entries


def parse_2026_sheet(ws) -> list[dict]:
    """Parse the combined 2026 sheet — has Bulan + Tanggal columns."""
    entries: list[dict] = []
    # Header row 1
    headers = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=1, column=c).value
        if v:
            headers[str(v).strip().lower()] = c
    col_bulan = headers.get("bulan")
    col_tanggal = headers.get("tanggal")
    col_lembaga = headers.get("nama lembaga")
    col_limbah = headers.get("nama limbah")
    col_volume = headers.get("volume")
    col_satuan = headers.get("satuan")
    col_kode = headers.get("kode limbah")
    col_kategori = headers.get("kategori")
    if not col_lembaga or not col_volume:
        return entries
    for r in range(2, ws.max_row + 1):
        lembaga = ws.cell(row=r, column=col_lembaga).value
        if not lembaga:
            continue
        bulan_raw = ws.cell(row=r, column=col_bulan).value if col_bulan else None
        tanggal_raw = ws.cell(row=r, column=col_tanggal).value if col_tanggal else None
        iso_date = fmt_date(tanggal_raw)
        month_iso = None
        if iso_date and re.match(r"^\d{4}-\d{2}-\d{2}$", iso_date):
            month_iso = iso_date[:7]
        elif bulan_raw:
            month_iso = parse_month_from_string(str(bulan_raw), default_year=2026)
        if not month_iso:
            continue
        volume = parse_number(ws.cell(row=r, column=col_volume).value)
        if volume is None:
            continue
        entries.append({
            "month": month_iso,
            "date": iso_date,
            "lembaga": str(lembaga).strip(),
            "limbah": str(ws.cell(row=r, column=col_limbah).value or "").strip(),
            "volume": round_to(float(volume), 3),
            "satuan": str(ws.cell(row=r, column=col_satuan).value or "").strip(),
            "kode_limbah": str(ws.cell(row=r, column=col_kode).value or "").strip(),
            "kategori": str(ws.cell(row=r, column=col_kategori).value or "").strip(),
        })
    return entries


def aggregate(entries: list[dict]) -> dict:
    """Compute summary + per-month + per-lembaga + per-kode aggregations."""
    from collections import defaultdict

    # Per month
    by_month: dict[str, dict] = defaultdict(lambda: {
        "entries": 0, "volume_liter": 0.0, "mass_kg": 0.0,
        "by_kategori": defaultdict(lambda: {"volume_liter": 0.0, "mass_kg": 0.0}),
    })
    # Per lembaga
    by_lembaga: dict[str, dict] = defaultdict(lambda: {
        "entries": 0, "volume_liter": 0.0, "mass_kg": 0.0,
    })
    # Per kode limbah
    by_kode: dict[str, dict] = defaultdict(lambda: {
        "entries": 0, "volume_liter": 0.0, "mass_kg": 0.0, "kategori": set(),
    })

    total_liter = total_kg = 0.0
    for e in entries:
        sat = (e["satuan"] or "").lower()
        kat = (e["kategori"] or "").lower() or "unknown"
        vol = float(e["volume"])
        m_key = e["month"]
        l_key = e["lembaga"]
        k_key = e["kode_limbah"] or "—"

        is_liter = sat.startswith("liter") or sat == "l"
        is_kg = sat in {"kg", "kilogram"}

        by_month[m_key]["entries"] += 1
        by_lembaga[l_key]["entries"] += 1
        by_kode[k_key]["entries"] += 1
        if e["kategori"]:
            by_kode[k_key]["kategori"].add(e["kategori"])

        if is_liter:
            by_month[m_key]["volume_liter"] += vol
            by_month[m_key]["by_kategori"][kat]["volume_liter"] += vol
            by_lembaga[l_key]["volume_liter"] += vol
            by_kode[k_key]["volume_liter"] += vol
            total_liter += vol
        elif is_kg:
            by_month[m_key]["mass_kg"] += vol
            by_month[m_key]["by_kategori"][kat]["mass_kg"] += vol
            by_lembaga[l_key]["mass_kg"] += vol
            by_kode[k_key]["mass_kg"] += vol
            total_kg += vol
        # Buah / other satuan: ignored from numeric totals

    def freeze_kategori_breakdown(d):
        return {k: {"volume_liter": round_to(v["volume_liter"], 2),
                    "mass_kg": round_to(v["mass_kg"], 2)} for k, v in d.items()}

    monthly_totals = [
        {
            "month": m,
            "label": month_label(m),
            "entries": d["entries"],
            "volume_liter": round_to(d["volume_liter"], 2),
            "mass_kg": round_to(d["mass_kg"], 2),
            "by_kategori": freeze_kategori_breakdown(d["by_kategori"]),
        }
        for m, d in sorted(by_month.items())
    ]
    lembaga_totals = sorted([
        {
            "lembaga": l,
            "entries": d["entries"],
            "volume_liter": round_to(d["volume_liter"], 2),
            "mass_kg": round_to(d["mass_kg"], 2),
        }
        for l, d in by_lembaga.items()
    ], key=lambda x: -(x["volume_liter"] + x["mass_kg"]))

    kode_totals = sorted([
        {
            "kode": k,
            "entries": d["entries"],
            "volume_liter": round_to(d["volume_liter"], 2),
            "mass_kg": round_to(d["mass_kg"], 2),
            "kategori": sorted(d["kategori"]),
        }
        for k, d in by_kode.items()
    ], key=lambda x: -(x["volume_liter"] + x["mass_kg"]))

    return {
        "summary": {
            "total_entries": len(entries),
            "total_volume_liter": round_to(total_liter, 2),
            "total_mass_kg": round_to(total_kg, 2),
            "unique_lembaga": len(by_lembaga),
            "unique_kode_limbah": len(by_kode),
            "months_with_data": len(by_month),
        },
        "monthly_totals": monthly_totals,
        "by_lembaga": lembaga_totals,
        "by_kode_limbah": kode_totals,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json")
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    try:
        import openpyxl
    except ImportError:
        print("[parse_b3_waste] openpyxl not installed; run: pip install openpyxl", file=sys.stderr)
        return 1

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_XLSX
    if not src.exists():
        print(f"[parse_b3_waste] source not found: {src}", file=sys.stderr)
        return 1

    wb = openpyxl.load_workbook(src, data_only=True)

    entries: list[dict] = []
    skipped_sheets: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Monthly report sheet?
        month_iso = month_from_sheet(sheet_name)
        if month_iso:
            entries.extend(parse_monthly_sheet(ws, month_iso))
            continue
        # 2026 combined sheet?
        if "2026" in sheet_name and "Laporan" in sheet_name:
            entries.extend(parse_2026_sheet(ws))
            continue
        # Wide TPS Logbook sheet — different shape, skip for now
        if "Logbook" in sheet_name:
            skipped_sheets.append(sheet_name)
            continue
        skipped_sheets.append(sheet_name)

    aggregated = aggregate(entries)

    if not entries:
        print("[parse_b3_waste] no entries parsed", file=sys.stderr)
        return 1

    # Period from entries
    months = sorted({e["month"] for e in entries})
    start = f"{months[0]}-01"
    # End: last day of last month (simple approximation)
    last_y, last_m = months[-1].split("-")
    last_dates = [e["date"] for e in entries if e["date"] and e["month"] == months[-1]]
    end = max(last_dates) if last_dates else f"{months[-1]}-28"

    flags = []
    if skipped_sheets:
        flags.append(flag(
            "info",
            f"Sheet TPS storage logbook (Limbah Masuk/Keluar/Sisa) tidak diolah ke dataset ini: {', '.join(skipped_sheets)}.",
        ))

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_XLSX],
        period={"start": start, "end": end},
    )
    data["data_quality_flags"] = flags
    data.update(aggregated)
    data["entries"] = entries

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    s = aggregated["summary"]
    print(
        f"[parse_b3_waste] wrote {target} "
        f"({s['total_entries']} entries, "
        f"{s['total_volume_liter']} L + {s['total_mass_kg']} kg, "
        f"{s['unique_lembaga']} lembaga, {s['unique_kode_limbah']} kode, "
        f"{s['months_with_data']} bulan, {len(flags)} flags)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
