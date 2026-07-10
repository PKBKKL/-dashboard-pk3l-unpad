"""Bangun timbulan.json dari buku besar (data/_ledger/timbulan.csv).

Menggantikan parse_timbulan_master.py. Buku besar adalah sumber kebenaran:
append-only, berformat teks, ikut git. Workbook Excel hanya kotak masuk yang
menambah baris lewat import_inbox.py.

Karena buku besar selalu memuat sejarah penuh, sifat "menimpa total" pada
write_json() berubah dari bahaya menjadi tidak berbahaya.

Nilai turunan dihitung di sini, tidak disimpan dua kali:
    unpad_kg = organik_anorganik + sisa_makanan + lingkungan + aset
    total_kg = unpad_kg + ipdn_kg
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ledger import ledger_dir, num, read_rows
from _utils import base_dataset, resolve_output, write_json

DATASET_ID = "timbulan"
CATEGORY_COLS = ["organik_anorganik", "sisa_makanan", "lingkungan", "aset"]
BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
DAY_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def build_daily(rows: list[dict]) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    for r in rows:
        iso = r["tanggal"].strip()
        if not iso:
            continue
        if iso in seen:
            raise SystemExit(f"[parse_{DATASET_ID}] tanggal ganda di buku besar: {iso}. ABORT.")
        seen.add(iso)

        cats = {c: round(num(r.get(f"{c}_kg")), 3) for c in CATEGORY_COLS}
        ipdn = round(num(r.get("ipdn_kg")), 3)
        unpad = round(sum(cats.values()), 3)
        total = round(unpad + ipdn, 3)
        if total == 0:
            continue

        d = dt.date.fromisoformat(iso)
        entries.append({
            "date": iso,
            "day_of_week": r.get("hari") or DAY_ID[d.weekday()],
            "total_kg": total,
            "unpad_kg": unpad,
            "ipdn_kg": ipdn,
            "by_category_kg": cats,
            "note": (r.get("catatan") or "").strip() or None,
            "quality_flag": (r.get("quality_flag") or "").strip() or None,
        })
    entries.sort(key=lambda e: e["date"])
    return entries


def build_monthly(daily: list[dict]) -> list[dict]:
    """Untuk setiap tahun yang punya data, terbitkan 12 bulan penuh —
    bulan tanpa data tampil sebagai total_kg: null."""
    years = sorted({int(e["date"][:4]) for e in daily})
    out: list[dict] = []
    for year in years:
        for mi in range(1, 13):
            month = f"{year}-{mi:02d}"
            dim = calendar.monthrange(year, mi)[1]
            ent = [e for e in daily if e["date"].startswith(month)]
            active = [e for e in ent if e["total_kg"] > 0 and e["quality_flag"] != "excluded_from_average"]
            sums = {c: round(sum(e["by_category_kg"][c] for e in ent), 3) for c in CATEGORY_COLS}
            unpad_kg = round(sum(e["unpad_kg"] for e in ent), 3)
            ipdn_kg = round(sum(e["ipdn_kg"] for e in ent), 3)
            total_kg = round(unpad_kg + ipdn_kg, 3)
            days_active = len(active)
            out.append({
                "month": month,
                "label": f"{BULAN_ID[mi - 1]} {year}",
                "total_kg": total_kg if total_kg else None,
                "organik_anorganik_kg": sums["organik_anorganik"],
                "sisa_makanan_kg": sums["sisa_makanan"],
                "lingkungan_kg": sums["lingkungan"],
                "aset_kg": sums["aset"],
                "avg_kg_per_calendar_day": round(total_kg / dim, 2) if dim and total_kg else None,
                "days_active": days_active,
                "days_in_month": dim,
                "avg_kg_per_active_day": round(total_kg / days_active, 2) if days_active else None,
                "category_breakdown_available": bool(any(sums.values())),
                "unpad_kg": unpad_kg,
                "ipdn_kg": ipdn_kg,
                "ipdn_active_days": sum(1 for e in ent if e["ipdn_kg"] > 0),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json dari buku besar")
    ap.add_argument("--ledger", default=None, help="Folder buku besar (default: data/_ledger)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    led = ledger_dir(args.ledger)
    src = led / "timbulan.csv"
    if not src.exists():
        raise SystemExit(
            f"[parse_{DATASET_ID}] buku besar tidak ditemukan: {src}\n"
            f"  Semai dulu:  python seed_ledger.py\n"
            f"  ABORT — timbulan.json TIDAK diubah."
        )

    daily = build_daily(read_rows(src))
    if not daily:
        raise SystemExit(
            f"[parse_{DATASET_ID}] buku besar tidak berisi satu pun hari dengan timbangan.\n"
            f"  Menolak menulis timbulan.json kosong. ABORT."
        )

    data = base_dataset(
        DATASET_ID,
        source_files=["_ledger/timbulan.csv"],
        period={"start": daily[0]["date"], "end": daily[-1]["date"]},
    )
    data["generated_at"] = dt.date.today().isoformat()
    data["data_quality_flags"] = [
        {"severity": r["severity"], "message": r["message"]}
        for r in read_rows(led / "timbulan_flags.csv")
    ]
    data["unit_default"] = "kg"
    data["vehicle_sources"] = [
        {k: v for k, v in {
            "id": r["id"], "label": r["label"], "operator": r["operator"],
            "tare_kg": int(r["tare_kg"]) if r["tare_kg"] else None,
            "note": r.get("note") or None,
        }.items() if k != "note" or v}
        for r in read_rows(led / "timbulan_kendaraan.csv")
    ]
    data["container_tare_kg"] = {r["kontainer"]: int(r["tare_kg"])
                                 for r in read_rows(led / "timbulan_tare.csv")}
    data["categories"] = [
        {"id": r["id"], "label": r["label"], "color_key": r["color_key"], "source": r["source"]}
        for r in read_rows(led / "timbulan_kategori.csv")
    ]
    data["monthly_summary"] = build_monthly(daily)
    data["daily_entries"] = daily

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)

    total = sum(e["total_kg"] for e in daily)
    active_months = sum(1 for m in data["monthly_summary"] if m["total_kg"])
    print(f"[parse_{DATASET_ID}] buku besar: {src}")
    print(f"[parse_{DATASET_ID}] wrote {target} ({len(daily)} hari, {active_months} bulan berisi, {total:,.0f} kg)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
