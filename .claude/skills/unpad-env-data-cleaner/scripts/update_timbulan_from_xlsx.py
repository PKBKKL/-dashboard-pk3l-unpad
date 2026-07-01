"""Targeted update: rebuild Feb (revised), Mei (extended), Juni (new) sections
of data/timbulan.json from the Excel workbook.

Preserves the existing structure and only touches monthly_summary + daily_entries
for the affected months. Recomputes avg_kg_per_active_day and
avg_kg_per_calendar_day for those months.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[4]
XLSX = ROOT / "Total Timbulan Sampah 2026  (Bulanan).xlsx"
JSON_PATH = ROOT / "data" / "timbulan.json"
DOCS_JSON_PATH = ROOT / "docs" / "data" / "timbulan.json"

DAY_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def hari_id(d: dt.date) -> str:
    return DAY_ID[d.weekday()]


def sum_row(row, indexes) -> float:
    tot = 0.0
    for i in indexes:
        if i < len(row):
            v = row[i]
            if isinstance(v, (int, float)):
                tot += v
    return tot


def extract_month(wb, sheet_name: str, iso_prefix: str, layout: dict) -> list[dict]:
    """Return list of daily entries for one month sheet.

    `layout` keys:
      total_unpad: int  (col index of Total UNPAD)
      total_ipdn:  int | None
      organik:     tuple[int, ...] | None  (cols to sum for organik/daun+ranting)
      sod:         tuple[int, ...] | None  (cols to sum for SOD)
    """
    ws = wb[sheet_name]
    entries: list[dict] = []
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
        tgl = row[1]
        if not isinstance(tgl, dt.datetime):
            continue
        iso = tgl.strftime("%Y-%m-%d")
        if not iso.startswith(iso_prefix):
            continue

        total_unpad = row[layout["total_unpad"]] if layout["total_unpad"] < len(row) else None
        total_unpad = float(total_unpad) if isinstance(total_unpad, (int, float)) else 0.0

        total_ipdn = 0.0
        if layout.get("total_ipdn") is not None:
            v = row[layout["total_ipdn"]] if layout["total_ipdn"] < len(row) else None
            if isinstance(v, (int, float)):
                total_ipdn = float(v)

        organik = sum_row(row, layout["organik"]) if layout.get("organik") else 0.0
        sod = sum_row(row, layout["sod"]) if layout.get("sod") else 0.0

        entry = {
            "date": iso,
            "day_of_week": hari_id(tgl.date()),
            "total_kg": round(total_unpad + total_ipdn, 3),
            "unpad_kg": round(total_unpad, 3),
            "ipdn_kg": round(total_ipdn, 3),
            "by_category_kg": None,
            "note": None,
            "quality_flag": None,
        }
        if organik or sod:
            anorganik = max(0.0, total_unpad - organik - sod)
            entry["by_category_kg"] = {
                "organik": round(organik, 3),
                "anorganik_residu": round(anorganik, 3),
                "sod": round(sod, 3),
            }
        entries.append(entry)
    return entries


def days_in_month(iso_prefix: str) -> int:
    y, m = map(int, iso_prefix.split("-"))
    if m == 12:
        return (dt.date(y + 1, 1, 1) - dt.date(y, 12, 1)).days
    return (dt.date(y, m + 1, 1) - dt.date(y, m, 1)).days


def rebuild_month_summary(month_iso: str, label: str, entries: list[dict],
                          category_available_prev: bool) -> dict:
    active = [e for e in entries if e["total_kg"] and e["total_kg"] > 0
              and e["quality_flag"] != "excluded_from_average"]
    days_active = len(active)
    dim = days_in_month(month_iso)
    unpad_kg = round(sum(e["unpad_kg"] for e in entries), 3)
    ipdn_kg = round(sum(e["ipdn_kg"] for e in entries), 3)
    total_kg = round(unpad_kg + ipdn_kg, 3)

    organik = round(sum((e["by_category_kg"] or {}).get("organik", 0)
                        for e in entries), 3)
    sod = round(sum((e["by_category_kg"] or {}).get("sod", 0)
                    for e in entries), 3)
    has_cat = any(e["by_category_kg"] for e in entries) or category_available_prev
    # Anorganik+residu = total UNPAD minus organik minus SOD (covers days
    # that had no explicit category split — all their waste is anorganik+residu).
    anorganik = round(max(0.0, unpad_kg - organik - sod), 3) if has_cat else 0

    ipdn_active_days = sum(1 for e in entries if e["ipdn_kg"] and e["ipdn_kg"] > 0)

    return {
        "month": month_iso,
        "label": label,
        "total_kg": total_kg,
        "organik_kg": organik if has_cat else 0,
        "anorganik_residu_kg": anorganik if has_cat else 0,
        "sod_kg": sod if has_cat else 0,
        "avg_kg_per_calendar_day": round(total_kg / dim, 2) if dim else None,
        "days_active": days_active,
        "days_in_month": dim,
        "avg_kg_per_active_day": round(total_kg / days_active, 2) if days_active else None,
        "category_breakdown_available": has_cat,
        "unpad_kg": unpad_kg,
        "ipdn_kg": ipdn_kg,
        "ipdn_active_days": ipdn_active_days,
    }


def main() -> int:
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    with JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Layouts per sheet (0-indexed cols, verified from headers dump)
    layouts = {
        "Februari": {
            "sheet": "Februari", "iso": "2026-02", "label": "Februari 2026",
            "layout": {"total_unpad": 20, "total_ipdn": None,
                       "organik": None, "sod": None},
            "prev_cat": True,   # keep old organik/anorganik/sod computed values? see below
        },
        "May": {
            "sheet": "May", "iso": "2026-05", "label": "Mei 2026",
            "layout": {"total_unpad": 16, "total_ipdn": 17,
                       "organik": (12, 13, 14), "sod": (15,)},
            "prev_cat": True,
        },
        "Juni": {
            "sheet": "Juni", "iso": "2026-06", "label": "Juni 2026",
            "layout": {"total_unpad": 18, "total_ipdn": 19,
                       "organik": (12, 13, 14), "sod": (15, 16, 17)},
            "prev_cat": False,
        },
    }

    # Extract fresh entries
    fresh_by_iso = {}
    fresh_summary = {}
    for key, cfg in layouts.items():
        entries = extract_month(wb, cfg["sheet"], cfg["iso"], cfg["layout"])
        fresh_by_iso[cfg["iso"]] = entries
        summ = rebuild_month_summary(cfg["iso"], cfg["label"], entries,
                                     cfg["prev_cat"])
        fresh_summary[cfg["iso"]] = summ

    # For Februari the sheet doesn't expose organik/anorganik per-day.
    # Preserve the previously-stored monthly organik/anorganik ratio and rescale
    # to match the new total (keeps chart continuity, only adjusts by delta).
    old_feb = next(m for m in data["monthly_summary"] if m["month"] == "2026-02")
    new_feb = fresh_summary["2026-02"]
    if old_feb["total_kg"] and new_feb["total_kg"]:
        ratio = new_feb["total_kg"] / old_feb["total_kg"]
        new_feb["organik_kg"] = round(old_feb.get("organik_kg", 0) * ratio, 2)
        new_feb["anorganik_residu_kg"] = round(
            old_feb.get("anorganik_residu_kg", 0) * ratio, 2)
        new_feb["sod_kg"] = round(old_feb.get("sod_kg", 0) * ratio, 2)
        new_feb["category_breakdown_available"] = old_feb.get(
            "category_breakdown_available", False)

    # Merge into JSON
    # 1) monthly_summary: replace matching iso entries in-place
    for i, m in enumerate(data["monthly_summary"]):
        if m["month"] in fresh_summary:
            data["monthly_summary"][i] = fresh_summary[m["month"]]

    # 2) daily_entries: drop Feb/Mei/Juni entries, then insert fresh
    keep = [e for e in data["daily_entries"] if e["date"][:7] not in fresh_by_iso]
    for iso, entries in fresh_by_iso.items():
        keep.extend(entries)
    keep.sort(key=lambda e: e["date"])
    data["daily_entries"] = keep

    # 3) Update period.end to the last active date
    active_dates = [e["date"] for e in data["daily_entries"] if e["total_kg"]]
    if active_dates:
        data["period"]["end"] = max(active_dates)

    # 4) Refresh generated_at
    data["generated_at"] = dt.date.today().isoformat()

    # 5) Update the "Februari & April jauh di atas Maret" flag message
    for f in data.get("data_quality_flags", []):
        if "Februari (99.644 kg)" in f.get("message", ""):
            f["message"] = (
                f["message"]
                .replace("Februari (99.644 kg)", "Februari (100.542 kg)")
            )

    # 6) Write back
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with DOCS_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Report
    print(f"[update_timbulan] wrote {JSON_PATH} + {DOCS_JSON_PATH}")
    ytd_total = 0
    ytd_active = 0
    for m in data["monthly_summary"]:
        if m["total_kg"]:
            ytd_total += m["total_kg"]
            ytd_active += m["days_active"]
            print(f"  {m['label']:15s} | total={m['total_kg']:>10.0f} | "
                  f"days_active={m['days_active']:>2} | "
                  f"avg_active={m['avg_kg_per_active_day']}")
    print(f"  {'TOTAL YTD':15s} | total={ytd_total:>10.0f} | "
          f"days_active={ytd_active}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
