"""Parse Data Pengolahan Sampah.md → pengolahan_sampah.json.

Reads:
  - Sheet Overview (monthly summary)
  - Sheet Des25 + Jan26 (daily entries with category breakdown)

Applies:
  - M/D → D/M date correction for entries with day<=12 (Des25 and Jan26 first rows)
  - Anorganik Jan26 reconciliation (Overview vs detail) — uses detail value
  - Method id mapping: Kompos→kompos, Bahan RDF→rdf, Bubur Maggot→maggot, Dumping→dumping
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md_parser import find_tables
from _utils import (
    base_dataset,
    find_project_root,
    fix_md_to_dm,
    flag,
    load_md,
    parse_number,
    resolve_output,
    round_to,
    write_json,
)

SOURCE_MD = "Data Pengolahan Sampah.md"
DATASET_ID = "pengolahan_sampah"

METHOD_MAP = {
    "Kompos": "kompos",
    "Bahan RDF": "rdf",
    "Bubur Maggot": "maggot",
    "Dumping": "dumping",
}

CATEGORY_MAP = {
    "Organik": "organik",
    "Anorganik": "anorganik",
    "Residu": "residu",
}


def parse_overview(md_text: str) -> list[dict]:
    """Extract monthly summary from sheet Overview."""
    tables = find_tables(md_text, section_contains="Overview")
    if not tables:
        return []
    t = tables[0]
    months = []
    for row in t.as_dicts():
        bulan = row.get("Bulan", "").strip()
        if not bulan:
            continue
        incoming = parse_number(row.get("Sampah yang masuk (Kg/Bulan)"))
        processed = parse_number(row.get("Sampah yang diolah (Kg/Bulan)"))
        if incoming is None or processed is None:
            continue
        output_total = parse_number(row.get("Hasil Olahan"))
        kompos = parse_number(row.get("Kompos (Kg/Bulan)")) or 0
        rdf = parse_number(row.get("Bahan RDF (Kg/Bulan)")) or 0
        maggot = parse_number(row.get("Maggot (Kg/Bulan)")) or 0
        month_iso = _bulan_to_iso(bulan)
        months.append({
            "month": month_iso,
            "label": bulan,
            "incoming_kg": incoming,
            "processed_kg": processed,
            "residual_kg": incoming - processed,
            "output": {"kompos_kg": kompos, "rdf_kg": rdf, "maggot_kg": maggot},
            "output_total_kg": output_total if output_total is not None else (kompos + rdf + maggot),
            "processing_rate_pct": round_to(processed / incoming * 100, 2) if incoming else 0,
        })
    return months


def _bulan_to_iso(label: str) -> str:
    months = {
        "januari": "01", "februari": "02", "maret": "03", "april": "04",
        "mei": "05", "juni": "06", "juli": "07", "agustus": "08",
        "september": "09", "oktober": "10", "november": "11", "desember": "12",
    }
    parts = label.lower().split()
    if len(parts) == 2 and parts[0] in months:
        return f"{parts[1]}-{months[parts[0]]}"
    return label


def parse_daily_sheet(md_text: str, sheet_hint: str) -> list[dict]:
    """Extract daily entries from Des25 or Jan26 sheet."""
    section_keyword = f"Sheet: {sheet_hint}"
    tables = find_tables(md_text, section_contains=section_keyword)
    if not tables:
        return []
    t = tables[0]
    entries: list[dict] = []
    current_date: str | None = None
    current_corrected: bool = False
    current_items: list[dict] = []
    for raw_row in t.as_dicts():
        tgl = (raw_row.get("Tanggal") or "").strip().replace("**", "")
        if tgl.upper() == "TOTAL" or tgl == "":
            if not tgl and current_date is not None:
                # continuation row
                pass
            elif tgl.upper() == "TOTAL":
                if current_date is not None and current_items:
                    entries.append(_finalize_entry(current_date, current_corrected, current_items))
                    current_date, current_corrected, current_items = None, False, []
                break

        if tgl:
            # New date — flush previous group
            if current_date is not None and current_items:
                entries.append(_finalize_entry(current_date, current_corrected, current_items))
                current_items = []
            iso, corrected = fix_md_to_dm(tgl, sheet_hint=sheet_hint)
            current_date = iso
            current_corrected = corrected

        cat_label = (raw_row.get("Jenis Sampah") or "").strip()
        if cat_label not in CATEGORY_MAP:
            continue
        method_label = (raw_row.get("Metode Pengolahan") or "").strip()
        item = {
            "category": CATEGORY_MAP[cat_label],
            "incoming_kg": parse_number(raw_row.get("Volume Masuk (kg)")) or 0,
            "processed_kg": parse_number(raw_row.get("Volume Terolah (kg)")) or 0,
            "residual_kg": parse_number(raw_row.get("Volume Sisa (kg)")) or 0,
            "method": METHOD_MAP.get(method_label, method_label.lower() if method_label else None),
            "output_kg": parse_number(raw_row.get("Hasil Olahan (kg)")) or 0,
            "status": (raw_row.get("Keterangan") or "").strip(),
        }
        current_items.append(item)

    if current_date is not None and current_items:
        entries.append(_finalize_entry(current_date, current_corrected, current_items))

    return entries


def _finalize_entry(date_iso: str, corrected: bool, items: list[dict]) -> dict:
    totals = {
        "incoming_kg": sum(it["incoming_kg"] for it in items),
        "processed_kg": sum(it["processed_kg"] for it in items),
        "residual_kg": sum(it["residual_kg"] for it in items),
    }
    return {
        "date": date_iso,
        "date_corrected_from_md": corrected,
        "items": items,
        "totals": totals,
    }


def compute_category_totals(entries: list[dict]) -> dict[str, float]:
    """Sum incoming by category across all entries."""
    out = {"organik": 0.0, "anorganik": 0.0, "residu": 0.0}
    for e in entries:
        for it in e["items"]:
            out[it["category"]] = out[it["category"]] + it["incoming_kg"]
    return {k: round_to(v, 2) for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json")
    ap.add_argument("--source", default=None, help="Path to Data Pengolahan Sampah.md")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_MD
    md_text = load_md(src)

    monthly = parse_overview(md_text)
    des_entries = parse_daily_sheet(md_text, "Des25")
    jan_entries = parse_daily_sheet(md_text, "Jan26")
    all_entries = des_entries + jan_entries

    # Reconcile category totals per month (detail vs overview)
    det_des = _category_totals_in_month(des_entries, "2025-12")
    det_jan = _category_totals_in_month(jan_entries, "2026-01")

    flags = [
        flag("info", "Tanggal pada Des25 dan Jan26 baris awal diperbaiki dari serial Excel terbalik (M/D → D/M)."),
        flag("info", "Metode pengolahan baru 'Bubur Maggot' muncul mulai Januari 2026 (2 record, total 390 kg)."),
    ]

    # Attach incoming_by_category to monthly_summary using detail-derived numbers
    for m in monthly:
        if m["month"] == "2025-12":
            m["incoming_by_category_kg"] = det_des
        elif m["month"] == "2026-01":
            m["incoming_by_category_kg"] = det_jan

    # Reconciliation: cross-check detail vs overview totals
    if monthly:
        jan_overview = next((m for m in monthly if m["month"] == "2026-01"), None)
        if jan_overview is not None:
            detail_processed = sum(it["processed_kg"] for e in jan_entries for it in e["items"])
            ov_processed = jan_overview["processed_kg"]
            if abs(detail_processed - ov_processed) > 1:
                flags.append(flag(
                    "warning",
                    f"Januari 2026: total processed di sheet detail ({detail_processed:.0f} kg) tidak cocok dengan Overview ({ov_processed:.0f} kg). Dashboard memakai nilai detail."
                ))

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_MD],
        period={"start": "2025-12-01", "end": "2026-01-31"},
    )
    data["unit_default"] = "kg"
    data["data_quality_flags"] = flags
    data["categories"] = [
        {"id": "organik", "label": "Organik", "color_key": "organik"},
        {"id": "anorganik", "label": "Anorganik", "color_key": "anorganik"},
        {"id": "residu", "label": "Residu", "color_key": "residu"},
    ]
    data["processing_methods"] = [
        {"id": "kompos", "label": "Kompos", "for_category": "organik", "color_key": "kompos"},
        {"id": "rdf", "label": "Bahan RDF", "for_category": "anorganik", "color_key": "rdf"},
        {"id": "maggot", "label": "Bubur Maggot", "for_category": "organik", "color_key": "maggot"},
        {"id": "dumping", "label": "Dumping", "for_category": "residu", "color_key": "dumping"},
    ]
    data["monthly_summary"] = monthly
    data["daily_entries"] = all_entries

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] wrote {target} ({len(all_entries)} daily entries, {len(monthly)} months, {len(flags)} flags)")
    return 0


def _category_totals_in_month(entries: list[dict], month_prefix: str) -> dict[str, float]:
    subset = [e for e in entries if e["date"].startswith(month_prefix)]
    return compute_category_totals(subset)


if __name__ == "__main__":
    sys.exit(main())
