"""Bangun traffic_accidents.json dari buku besar (data/_ledger/traffic_accidents.csv).

Menggantikan parse_traffic_accidents_xlsx.py. Buku besar adalah sumber
kebenaran: append-only, berformat teks, ikut git. Workbook Excel hanya kotak
masuk yang menambah baris lewat import_inbox.py.

Tahun tidak di-hardcode: ia dibaca dari kolom `tahun` di buku besar.
Spec 1.1 — field `incidents_detail` dengan `year` di tiap baris.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ledger import ledger_dir, read_rows
from _utils import base_dataset, resolve_output, write_json

DATASET_ID = "traffic_accidents"


def build_fatality_index(rows: list[dict]) -> dict[tuple[int, str], dict[str, int]]:
    """Indeks fatalitas per (tahun, bulan) -> {jenis: jumlah}.

    Sumbernya buku besar tersendiri (`traffic_accidents_fatality.csv`), bukan
    kolom di buku besar kasus. Dipisah karena fatalitas dicatat manual dengan
    provenance sendiri: pencatatan bulanan di workbook tidak memuat kolom
    fatalitas, hanya keterangan mengapung di bawah tabel.
    """
    idx: dict[tuple[int, str], dict[str, int]] = {}
    for r in rows:
        jml = int(r["jumlah"])
        if jml <= 0:
            continue
        key = (int(r["tahun"]), r["bulan"])
        per_jenis = idx.setdefault(key, {})
        per_jenis[r["jenis"]] = per_jenis.get(r["jenis"], 0) + jml
    return idx


def check_fatality(yearly: list[dict], fatality: dict[tuple[int, str], dict[str, int]]) -> None:
    """Gagal keras bila fatalitas tidak punya kasus yang menaunginya.

    Fatalitas lebih banyak daripada kasus, atau fatalitas pada (bulan, jenis)
    yang tidak mencatat satu kasus pun, berarti salah satu dari dua buku besar
    keliru. Jangan diterbitkan: angka kematian di rekam jejak publik tidak
    boleh menggantung tanpa kasusnya.
    """
    kasus = {
        (y["year"], m["month"]): m["by_type"]
        for y in yearly for m in y["monthly"]
    }
    masalah: list[str] = []
    for (year, month), per_jenis in sorted(fatality.items()):
        ada = kasus.get((year, month), {})
        for jenis, jml in sorted(per_jenis.items()):
            if jenis not in ada:
                masalah.append(
                    f"{month} '{jenis}': {jml} fatalitas tetapi TIDAK ADA kasus "
                    f"pada bulan/jenis itu di traffic_accidents.csv")
            elif jml > ada[jenis]:
                masalah.append(
                    f"{month} '{jenis}': {jml} fatalitas melebihi {ada[jenis]} kasus")
    if masalah:
        detail = "\n".join(f"    - {m}" for m in masalah)
        raise SystemExit(
            f"\n[parse_traffic_accidents_ledger] GAGAL KERAS — fatalitas tidak cocok "
            f"dengan kasus:\n{detail}\n"
            f"  Perbaiki data/_ledger/traffic_accidents_fatality.csv atau "
            f"traffic_accidents.csv, lalu ulangi.\n")


def build_yearly(rows: list[dict], jenis_order: list[str],
                 fatality: dict[tuple[int, str], dict[str, int]] | None = None) -> list[dict]:
    fatality = fatality or {}
    per_year: dict[int, dict[str, dict[str, int]]] = {}
    for r in rows:
        jml = int(r["jumlah"])
        if jml <= 0:
            continue
        year = int(r["tahun"])
        per_year.setdefault(year, {}).setdefault(r["bulan"], {})[r["jenis"]] = jml

    yearly: list[dict] = []
    years = sorted(per_year)
    latest = years[-1] if years else None
    for year in years:
        monthly = []
        for month in sorted(per_year[year]):
            types = per_year[year][month]
            # Urutan kunci mengikuti kamus jenis, bukan urutan baris CSV.
            ordered = {j: types[j] for j in jenis_order if j in types}
            ordered.update({j: v for j, v in types.items() if j not in ordered})
            fat = fatality.get((year, month), {})
            # Fatalitas mengikuti urutan jenis yang sama, dan hanya memuat
            # jenis yang benar-benar tercatat memakan korban.
            fat_ordered = {j: fat[j] for j in ordered if j in fat}
            fat_ordered.update({j: v for j, v in fat.items() if j not in fat_ordered})
            entry_m = {
                "month": month,
                "by_type": ordered,
                "total": sum(ordered.values()),
                "fatalities": sum(fat_ordered.values()),
            }
            if fat_ordered:
                entry_m["fatalities_by_type"] = fat_ordered
            monthly.append(entry_m)
        total = sum(m["total"] for m in monthly)
        entry = {
            "year": year,
            "monthly": monthly,
            "total_yearly_computed": total,
            "total_yearly_reported": total,
            "total_fatalities": sum(m["fatalities"] for m in monthly),
        }
        if year == latest and monthly:
            entry["ytd_through_month"] = monthly[-1]["month"]
        yearly.append(entry)
    return yearly


def build_detail(rows: list[dict]) -> list[dict]:
    out = []
    for r in sorted(rows, key=lambda x: (int(x["tahun"]), int(x["no"]))):
        e = {
            "no": int(r["no"]),
            "year": int(r["tahun"]),
            "month": r["bulan"],
            "type": r["jenis"] or None,
            "location_id": r["lokasi_id"],
            "location_label_raw": r["lokasi_label"],
            "count": int(r["jumlah"]),
        }
        if (r.get("catatan") or "").strip():
            e["note"] = r["catatan"].strip()
        out.append(e)
    return out


def _months(yearly: list[dict]) -> list[str]:
    return sorted(m["month"] for y in yearly for m in y["monthly"] if m["total"] > 0)


def _period(yearly: list[dict]) -> dict:
    months = _months(yearly)
    if not months:
        raise SystemExit(f"[parse_{DATASET_ID}] tidak ada bulan aktif. ABORT.")
    ys, ms = map(int, months[0].split("-"))
    ye, me = map(int, months[-1].split("-"))
    nxt = dt.date(ye + (1 if me == 12 else 0), 1 if me == 12 else me + 1, 1)
    return {"start": dt.date(ys, ms, 1).isoformat(),
            "end": (nxt - dt.timedelta(days=1)).isoformat()}


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json dari buku besar")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    led = ledger_dir(args.ledger)
    src = led / "traffic_accidents.csv"
    if not src.exists():
        raise SystemExit(
            f"[parse_{DATASET_ID}] buku besar tidak ditemukan: {src}\n"
            f"  Semai dulu:  python seed_ledger.py\n"
            f"  ABORT — traffic_accidents.json TIDAK diubah."
        )

    jenis = read_rows(led / "traffic_accidents_jenis.csv")
    jenis_order = [j["id"] for j in jenis]

    # Buku besar fatalitas bersifat opsional: repo yang belum memilikinya tetap
    # membangun JSON yang sah, dengan fatalities = 0 di tiap bulan.
    fat_src = led / "traffic_accidents_fatality.csv"
    fatality = build_fatality_index(read_rows(fat_src)) if fat_src.exists() else {}

    yearly = build_yearly(read_rows(src), jenis_order, fatality)
    if not yearly or all(y["total_yearly_computed"] == 0 for y in yearly):
        raise SystemExit(f"[parse_{DATASET_ID}] tidak ada satu pun kasus di buku besar. "
                         f"Menolak menulis output kosong. ABORT.")
    check_fatality(yearly, fatality)

    detail = build_detail(read_rows(led / "traffic_accidents_detail.csv"))

    sources = ["_ledger/traffic_accidents.csv"]
    if fatality:
        sources.append("_ledger/traffic_accidents_fatality.csv")
    data = base_dataset(DATASET_ID, source_files=sources,
                        period=_period(yearly))
    data["generated_at"] = dt.date.today().isoformat()
    data["data_quality_flags"] = [
        {"severity": r["severity"], "message": r["message"]}
        for r in read_rows(led / "traffic_accidents_flags.csv")
    ]
    data["vehicle_types"] = [{"id": j["id"], "label": j["label"]} for j in jenis]
    data["yearly"] = yearly
    data["incidents_detail"] = detail

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] buku besar: {src}")
    print(f"[parse_{DATASET_ID}] wrote {target} (" +
          ", ".join(f"{y['year']}: {y['total_yearly_computed']}" for y in yearly) +
          f", {len(detail)} detail lokasi, " +
          f"{sum(y['total_fatalities'] for y in yearly)} fatalitas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
