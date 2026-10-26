"""Parse Laporan Hasil Uji Udara Ambien dan Kebisingan ... .md → air_quality.json.

Sumbernya transkrip Markdown di root repo, bukan PDF — PDF di-gitignore sehingga
repo tidak boleh bergantung padanya. Pola ini sama dengan parse_water_quality.py.

Ambang baku mutu TIDAK diambil dari peraturan mana pun; ia dibaca apa adanya dari
kolom "Baku Mutu" di LHU. Untuk Pb, PM 2.5, PM 10, dan kebisingan, LHU menulis "-",
sehingga parameter itu TIDAK dinilai kepatuhannya dan selisihnya diterbitkan sebagai
data_quality_flag. Mengarang angka baku mutu ke rekam jejak publik tidak dilakukan.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import base_dataset, find_project_root, flag, resolve_output, write_json

DATASET_ID = "air_quality"
SOURCE_MD = "Laporan Hasil Uji Udara Ambien dan Kebisingan PK3L UNPAD Juli 2026.md"

BULAN = {"januari":1,"februari":2,"maret":3,"april":4,"mei":5,"juni":6,
         "juli":7,"agustus":8,"september":9,"oktober":10,"november":11,"desember":12}

# nama parameter di LHU -> id, label tayang, kategori
PARAM = {
    "Sulfur Dioksida (SO2)":   ("so2",  "Sulfur Dioksida (SO₂)",   "gas"),
    "Nitrogen Dioksida (NO2)": ("no2",  "Nitrogen Dioksida (NO₂)", "gas"),
    "Oksidan (O3)":            ("o3",   "Oksidan (O₃)",            "gas"),
    "TSP":                     ("tsp",  "Total Suspended Particulate (TSP)", "partikulat"),
    "Pb":                      ("pb",   "Timbal (Pb)",             "logam"),
    "PM 2.5":                  ("pm25", "PM 2,5",                  "partikulat"),
    "PM 10":                   ("pm10", "PM 10",                   "partikulat"),
    "Kebisingan Lingkungan (Sesaat)": ("kebisingan", "Kebisingan Lingkungan", "fisika"),
}
SATUAN = {"µg/m3": "µg/m³", "mg/m3": "mg/m³", "dBa": "dBA"}

# Urutan tayang mengikuti urutan di LHU, bukan abjad.
URUT = {pid: i for i, (pid, _, _) in enumerate(PARAM.values())}


def dms_ke_desimal(dms: str) -> tuple[float | None, float | None]:
    """'06°54’46.0”S 107°46’27.6”E' -> (-6.912778, 107.774333)."""
    pola = re.compile(r"(\d+)\s*°\s*(\d+)\s*[’'′]\s*([\d.]+)\s*[”\"″]\s*([NSEW])")
    out = {}
    for d, m, s, arah in pola.findall(dms):
        nilai = int(d) + int(m) / 60 + float(s) / 3600
        if arah in ("S", "W"):
            nilai = -nilai
        out["lat" if arah in ("N", "S") else "lon"] = round(nilai, 6)
    return out.get("lat"), out.get("lon")


def tanggal_id(teks: str) -> str | None:
    """'15 Juli 2026' -> '2026-07-15'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", teks)
    if not m:
        return None
    bln = BULAN.get(m.group(2).lower())
    return f"{m.group(3)}-{bln:02d}-{int(m.group(1)):02d}" if bln else None


def rentang_tanggal(teks: str) -> dict:
    """'10-11 Juli 2026' / '15 – 21 Juli 2026' / '10 Juli 2026' -> {start, end}."""
    m = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", teks)
    if m:
        bln = BULAN.get(m.group(3).lower())
        return {"start": f"{m.group(4)}-{bln:02d}-{int(m.group(1)):02d}",
                "end": f"{m.group(4)}-{bln:02d}-{int(m.group(2)):02d}"}
    satu = tanggal_id(teks)
    return {"start": satu, "end": satu}


def angka(teks: str):
    """'14.01' -> 14.01 · '<0.04' -> (0.04, True) · 'tidak dicantumkan'/'-' -> None."""
    teks = teks.strip()
    if teks in ("-", "", "tidak dicantumkan"):
        return None, False
    lod = teks.startswith("<")
    try:
        return float(teks.lstrip("<").replace(",", ".")), lod
    except ValueError:
        return None, False


def tampil(v: float | None, lod: bool) -> str:
    if v is None:
        return "–"
    s = f"{v:g}".replace(".", ",")
    return f"<{s}" if lod else s


def baca_blok(md: str) -> list[dict]:
    """Pecah MD jadi satu blok per LHU."""
    bagian = re.split(r"\n---\n", md)
    out = []
    for b in bagian:
        m = re.search(r"^##\s+(\S+)", b, re.M)
        if not m:
            continue
        out.append({"report_no": m.group(1), "teks": b})
    return out


def field(teks: str, nama: str) -> str | None:
    m = re.search(rf"^-\s+\*\*{re.escape(nama)}:\*\*\s*(.+?)\s*$", teks, re.M)
    return m.group(1).strip() if m else None


def baris_tabel(teks: str, awal: str) -> list[list[str]]:
    """Ambil baris isi tabel markdown yang kepalanya diawali `awal`."""
    out, aktif = [], False
    for ln in teks.splitlines():
        ln = ln.strip()
        if ln.startswith("| No | Parameter") if awal == "param" else ln.startswith("| Parameter |"):
            aktif = True
            continue
        if aktif:
            if not ln.startswith("|"):
                break
            sel = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(sel)) <= set("-: "):
                continue
            out.append(sel)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json")
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_MD
    if not src.exists():
        raise SystemExit(
            f"[parse_{DATASET_ID}] sumber tidak ditemukan: {src}\n"
            f"  ABORT — air_quality.json TIDAK diubah."
        )
    md = src.read_text(encoding="utf-8")

    param_dict: dict[str, dict] = {}
    lokasi_map: dict[str, dict] = {}
    reports: list[dict] = []
    tanpa_u95: list[str] = []
    lod_pb = 0

    for blok in baca_blok(md):
        t = blok["teks"]
        jenis_raw = field(t, "Jenis sampel") or ""
        sample_type = "udara_ambien" if "Ambien" in jenis_raw else "kebisingan_lingkungan"
        lok_raw = field(t, "Lokasi sampling") or ""
        dms = field(t, "Titik koordinat") or ""
        lat, lon = dms_ke_desimal(dms)
        lok_id = re.sub(r"[^a-z0-9]+", "-",
                        lok_raw.lower().split("(")[0].strip()).strip("-")
        lokasi_map.setdefault(lok_id, {
            "id": lok_id, "label": lok_raw, "lat": lat, "lon": lon,
            "coordinates_dms": dms,
        })

        kode_full = field(t, "Kode sampel") or ""
        mk = re.match(r"(\S+)\s*\(([^)]+)\)", kode_full)
        baku_raw = field(t, "Baku mutu") or "-"

        measurements = []
        for sel in baris_tabel(t, "param"):
            if len(sel) < 8:
                continue
            _, nama, waktu, hasil, satuan, baku, metode, u95 = sel[:8]
            nama_bersih = nama.rstrip("*").strip()
            if nama_bersih not in PARAM:
                raise SystemExit(
                    f"\n[parse_{DATASET_ID}] GAGAL KERAS — parameter tak dikenal: "
                    f"{nama_bersih!r} pada {blok['report_no']}.\n"
                    f"  Daftarkan dulu di PARAM, jangan dibuang diam-diam.\n")
            pid, label, kategori = PARAM[nama_bersih]
            unit = SATUAN.get(satuan, satuan)
            param_dict.setdefault(pid, {"label": label, "unit": unit,
                                        "category": kategori, "averaging_time": waktu})
            nilai, lod = angka(hasil)
            ambang, _ = angka(baku)
            thr = {"type": "max", "max": ambang} if ambang is not None else None
            patuh = None
            if thr is not None and nilai is not None:
                patuh = nilai <= ambang
            u, _ = angka(u95)
            if u is None and u95.strip() not in ("-",):
                tanpa_u95.append(f"{blok['report_no']} · {label}")
            if pid == "pb" and lod:
                lod_pb += 1
            measurements.append({
                "parameter_id": pid, "parameter_label": label, "category": kategori,
                "unit": unit, "averaging_time": waktu,
                "result": nilai, "result_display": tampil(nilai, lod),
                "below_detection_limit": lod,
                "threshold": thr, "compliant": patuh,
                "method": metode, "uncertainty_u95": u,
            })
        measurements.sort(key=lambda m: URUT.get(m["parameter_id"], 99))

        klim = []
        for sel in baris_tabel(t, "klim"):
            if len(sel) == 4:
                klim.append({"parameter": sel[0], "value_1h": sel[1],
                             "value_24h": sel[2], "unit": sel[3]})
            elif len(sel) == 3:
                klim.append({"parameter": sel[0], "value": sel[1], "unit": sel[2]})

        dinilai = [m for m in measurements if m["compliant"] is not None]
        tidak_patuh = [m["parameter_id"] for m in dinilai if m["compliant"] is False]
        reports.append({
            "report_no": blok["report_no"],
            "sample_code": mk.group(1) if mk else kode_full,
            "sample_label": mk.group(2) if mk else None,
            "sample_type": sample_type,
            "location_id": lok_id,
            "location_label_raw": lok_raw,
            "coordinates_dms": dms, "lat": lat, "lon": lon,
            "regulation_raw": baku_raw,
            "sampling_date": rentang_tanggal(field(t, "Tanggal sampling") or ""),
            "received_date": tanggal_id(field(t, "Tanggal terima sampel") or ""),
            "testing_period": rentang_tanggal(field(t, "Tanggal analisis") or ""),
            "report_date": "2026-07-22",
            "measurements": measurements,
            "climatology": klim,
            "summary": {
                "total_parameters": len(measurements),
                "parameters_with_threshold": len(dinilai),
                "compliant_count": sum(1 for m in dinilai if m["compliant"]),
                "non_compliant_count": len(tidak_patuh),
                "non_compliant_parameters": tidak_patuh,
                "compliance_pct": round(
                    sum(1 for m in dinilai if m["compliant"]) / len(dinilai) * 100, 2)
                    if dinilai else None,
            },
        })

    if not reports:
        raise SystemExit(f"[parse_{DATASET_ID}] tidak ada satu pun LHU terbaca. ABORT.")

    # ── ringkasan lintas LHU ──────────────────────────────────────────
    per_jenis = {}
    for jenis in ("udara_ambien", "kebisingan_lingkungan"):
        rr = [r for r in reports if r["sample_type"] == jenis]
        if not rr:
            continue
        pcts = [r["summary"]["compliance_pct"] for r in rr
                if r["summary"]["compliance_pct"] is not None]
        ringkas = {
            "reports": len(rr),
            "locations": len({r["location_id"] for r in rr}),
            "compliance_pct_avg": round(sum(pcts) / len(pcts), 2) if pcts else None,
            "common_exceedances": sorted({p for r in rr
                                          for p in r["summary"]["non_compliant_parameters"]}),
        }
        if jenis == "kebisingan_lingkungan":
            nilai = [m["result"] for r in rr for m in r["measurements"]
                     if m["parameter_id"] == "kebisingan" and m["result"] is not None]
            if nilai:
                ringkas["noise_min_dba"] = min(nilai)
                ringkas["noise_max_dba"] = max(nilai)
                ringkas["noise_avg_dba"] = round(sum(nilai) / len(nilai), 2)
        per_jenis[jenis] = ringkas

    semua_tgl = [r["sampling_date"]["start"] for r in reports if r["sampling_date"]["start"]] + \
                [r["sampling_date"]["end"] for r in reports if r["sampling_date"]["end"]]
    data = base_dataset(DATASET_ID, source_files=[SOURCE_MD],
                        period={"start": min(semua_tgl), "end": "2026-07-22"})
    data["generated_at"] = dt.date.today().isoformat()

    tanpa_ambang = sorted({m["parameter_label"] for r in reports
                           for m in r["measurements"] if m["threshold"] is None})
    flags = [flag("info",
                  "Baku mutu diambil apa adanya dari kolom “Baku Mutu” di LHU, bukan dari "
                  "teks peraturan. Parameter yang di LHU tertulis “-” tidak dinilai "
                  f"kepatuhannya: {', '.join(tanpa_ambang)}.")]
    if lod_pb:
        flags.append(flag("info",
                          f"Timbal (Pb) pada {lod_pb} titik tercatat di bawah batas deteksi "
                          f"metode (<0,04 µg/m³); nilainya dicatat sebagai batas deteksi."))
    if tanpa_u95:
        flags.append(flag("warning",
                          "Ketidakpastian (U95) tidak dicantumkan di laporan asli untuk: "
                          + "; ".join(tanpa_u95) + "."))
    flags.append(flag("info",
                      "Baru tersedia satu periode sampling (10–14 Juli 2026), sehingga "
                      "perbandingan antar waktu belum dapat ditampilkan."))
    data["data_quality_flags"] = flags

    data["issuing_lab"] = {
        "name": "PT Akalab Mahardika Indonesia",
        "head": "Tri Hadhi Nugroho",
        "technical_manager": "Galih Noviar Pratama",
        "report_place_date": "Sleman, 22 Juli 2026",
        "sampling_method_ambient": "SNI 19.7119.6-2005",
    }
    data["parameter_dictionary"] = param_dict
    data["locations"] = sorted(lokasi_map.values(), key=lambda x: x["id"])
    data["sample_type_label"] = {
        "udara_ambien": "Udara Ambien",
        "kebisingan_lingkungan": "Kebisingan Lingkungan",
    }
    data["reports"] = reports
    data["aggregate_summary"] = {"by_sample_type": per_jenis}

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] sumber: {src}")
    print(f"[parse_{DATASET_ID}] wrote {target} "
          f"({len(reports)} LHU, {len(data['locations'])} titik, "
          f"{sum(len(r['measurements']) for r in reports)} pengukuran, {len(flags)} flags)")
    for j, v in per_jenis.items():
        print(f"[parse_{DATASET_ID}]   {j}: {v['reports']} LHU, "
              f"kepatuhan {v['compliance_pct_avg']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
