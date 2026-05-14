"""Parse Scan Sertifikat...Oktober 2025.md → water_quality.json.

Reads 9 LHU sections, each with:
  - Header table (Item | Keterangan)
  - Parameter table (NO | PARAMETER | SATUAN | HASIL | BAKU MUTU | ACUAN METODE)
    - LHU 8 (RS UNPAD) has two BAKU MUTU columns (Gol. I, Gol. II)

Normalizes:
  - Parameter labels → ids (via resources/parameter_thresholds.json)
  - Threshold parsing into {type, ...}
  - Scientific notation (24 x 10⁷ → 240000000)
  - Below-detection-limit prefix '<'
  - 'Tidak Berbau' qualitative
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md_parser import find_tables, parse_md
from _utils import (
    RESOURCES_DIR,
    base_dataset,
    find_project_root,
    flag,
    load_md,
    parse_number,
    read_json,
    resolve_output,
    round_to,
    write_json,
)

SOURCE_MD = "Scan Sertifikat Hasil Uji Air Permukaan, Air Limbah, dan Air Tanah PK3L UNPAD Oktober 2025.md"
DATASET_ID = "water_quality"

PARAMETER_LABEL_TO_ID = {
    "Suhu": "suhu",
    "Daya Hantar Listrik (DHL)": "dhl",
    "Padatan Tersuspensi Total (TSS)": "tss",
    "Padatan Terlarut Total (TDS)": "tds",
    "Kekeruhan": "kekeruhan",
    "Warna": "warna",
    "Bau": "bau",
    "pH": "ph",
    "Kesadahan (CaCO₃)": "kesadahan",
    "Klorida": "klorida",
    "Besi (Fe)": "fe",
    "Mangan (Mn)": "mn",
    "Nikel (Ni)": "ni",
    "Seng (Zn)": "zn",
    "Tembaga (Cu)": "cu",
    "Krom Total (Cr)": "cr_total",
    "Kromium valensi 6 (Cr⁶⁺)": "cr6",
    "Kadmium (Cd)": "cd",
    "Timbal (Pb)": "pb",
    "BOD": "bod",
    "COD": "cod",
    "Oksigen Terlarut (DO)": "do",
    "Total Nitrogen": "tn",
    "Nitrat sebagai N (NO₃-N)": "no3_n",
    "Nitrit sebagai N (NO₂-N)": "no2_n",
    "Orto Fosfat (PO₄³⁻)": "po4",
    "Minyak dan Lemak": "minyak_lemak",
    "MPN E. coli": "mpn_ecoli",
    "MPN Coliform": "mpn_coliform",
    "E. coli": "ecoli_cfu",
    "Total Coliform": "coliform_cfu",
}

LOCATION_MAP = {
    "Sekebitung": ("sekebitung", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Outlet Ciparanje": ("outlet-ciparanje", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Badan Air Embung": ("embung", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Inlet Ekoriparian": ("inlet-ekoriparian", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Badan Air Ekoriparian": ("badan-ekoriparian", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Outlet Ekoriparian": ("outlet-ekoriparian", "air_permukaan", "ppri-22-2021-vi-kelas-2"),
    "Outlet IPAL Prodi Kimia (Klinik)": ("ipal-kimia", "air_limbah", "permen-lh-5-2014-xliv"),
    "Outlet IPAL Rumah Sakit Universitas Padjadjaran": ("ipal-rs", "air_limbah", "permen-lh-5-2014-xlvii"),
    "Sumur Pantau": ("sumur-pantau", "air_sumur", "permenkes-2-2023"),
}


def parse_scientific(s: str) -> tuple[int, str]:
    """Parse '24 x 10⁷' or '24 × 10⁷' → (240000000, display)."""
    s_norm = s.replace("×", "x").replace("X", "x")
    m = re.match(r"^\s*([\d.,]+)\s*x\s*10([⁰¹²³⁴⁵⁶⁷⁸⁹0-9]+)\s*$", s_norm)
    if not m:
        return None, s
    base = parse_number(m.group(1))
    exp_str = m.group(2)
    super_to_digit = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    exp = int(exp_str.translate(super_to_digit))
    return int(base * (10 ** exp)), s.replace("x", "×").strip()


def parse_result(raw: str) -> dict:
    """Parse the HASIL ANALISA cell into structured result."""
    s = raw.strip()
    flagged = False
    if "^" in s:
        flagged = True
        s = s.replace("^", "").strip()

    if not s:
        return {"result": None, "result_display": "", "below_detection_limit": False, "source_flagged_exceedance": flagged}

    # Qualitative
    if re.search(r"berbau", s, re.IGNORECASE):
        return {"result": s, "result_display": s, "below_detection_limit": False, "source_flagged_exceedance": flagged, "qualitative": True}

    # Below detection
    below = False
    if s.startswith("<"):
        below = True
        s = s.lstrip("<").strip()

    # Scientific
    sci_val, sci_disp = parse_scientific(s)
    if sci_val is not None:
        return {
            "result": sci_val,
            "result_display": sci_disp,
            "below_detection_limit": below,
            "source_flagged_exceedance": flagged,
        }

    val = parse_number(s)
    return {
        "result": val,
        "result_display": raw.strip(),
        "below_detection_limit": below,
        "source_flagged_exceedance": flagged,
    }


def parse_threshold(raw: str, parameter_id: str, param_dict: dict) -> dict | None:
    """Parse BAKU MUTU cell into threshold object."""
    s = raw.strip()
    if not s or s in {"-", "—"}:
        return None
    s_lower = s.lower()
    # Range
    m = re.match(r"^\s*([\d.,]+)\s*-\s*([\d.,]+)\s*$", s)
    if m:
        return {"type": "range", "min": parse_number(m.group(1)), "max": parse_number(m.group(2))}
    # Deviation: 'Dev 3' or 'Suhu Udara ± 3°C'
    if "dev" in s_lower or "±" in s_lower or "udara" in s_lower:
        m = re.search(r"(\d+(?:[.,]\d+)?)", s)
        if m:
            return {"type": "deviation", "max_dev": parse_number(m.group(1)), "reference": "ambient"}
    # Qualitative
    if re.search(r"berbau|tidak\s+berbau", s_lower):
        return {"type": "qualitative", "expected": "Tidak Berbau"}
    # Less than: '< 300' or '< 3'
    m = re.match(r"^\s*<\s*([\d.,]+)\s*$", s)
    if m:
        return {"type": "max", "max": parse_number(m.group(1))}

    # Plain number
    val = parse_number(s)
    if val is None:
        return None

    # Decide direction from parameter dict
    direction = param_dict.get(parameter_id, {}).get("direction", "max")
    if direction == "min":
        return {"type": "min", "min": val}
    return {"type": "max", "max": val}


def compute_compliant(result_val, threshold: dict | None, below_dl: bool, qualitative_val=None) -> bool | None:
    """Compute compliance using correct threshold direction."""
    if threshold is None:
        return None
    if qualitative_val is not None and threshold.get("type") == "qualitative":
        expected = threshold.get("expected", "").lower()
        return expected in str(qualitative_val).lower()
    if result_val is None:
        return None
    if below_dl:
        # Below detection limit is always compliant for max-type thresholds
        if threshold.get("type") in {"max", "range"}:
            return True
    ttype = threshold.get("type")
    if ttype == "max":
        return result_val <= threshold["max"]
    if ttype == "min":
        return result_val >= threshold["min"]
    if ttype == "range":
        return threshold["min"] <= result_val <= threshold["max"]
    if ttype == "deviation":
        # Without ambient reference value at compute time, treat as compliant if not flagged
        return None
    return None


def extract_lhu_sections(md_text: str) -> list[dict]:
    """Return list of LHU dicts."""
    all_tables = parse_md(md_text)
    # Group by top-level heading "## N. LAPORAN HASIL UJI ..."
    sections: list[tuple[str, list]] = []
    current_title: str | None = None
    current_tables: list = []
    for t in all_tables:
        section_title = next((s for s in t.section_path if s.startswith(tuple(f"{n}. LAPORAN" for n in range(1, 10)))), None)
        if section_title and section_title != current_title:
            if current_title:
                sections.append((current_title, current_tables))
            current_title = section_title
            current_tables = []
        if section_title:
            current_tables.append(t)
    if current_title:
        sections.append((current_title, current_tables))

    lhus = []
    for title, tables in sections:
        header_table = tables[0] if tables else None
        param_table = tables[1] if len(tables) > 1 else None
        if not header_table or not param_table:
            continue
        header = {row["Item"].strip(): row.get("Keterangan", "").strip() for row in header_table.as_dicts() if "Item" in row}
        lhus.append({
            "title": title,
            "report_no": title.split("No.", 1)[1].strip() if "No." in title else title,
            "header": header,
            "param_table": param_table,
        })
    return lhus


def build_report(lhu: dict, param_dict: dict) -> dict:
    header = lhu["header"]
    raw_loc = header.get("Lokasi Pengambilan Sampel", "")
    loc_id, sample_type, regulation_id = LOCATION_MAP.get(raw_loc, (None, None, None))

    measurements: list[dict] = []
    in_class_split = "BAKU MUTU Gol. I" in lhu["param_table"].headers

    for row in lhu["param_table"].as_dicts():
        param_label_raw = (row.get("PARAMETER") or "").strip().replace("**", "").strip()
        # Skip category header rows
        if not param_label_raw or param_label_raw in {"FISIKA", "KIMIA", "BIOLOGI", "MIKROBIOLOGI"}:
            continue
        param_id = PARAMETER_LABEL_TO_ID.get(param_label_raw)
        if not param_id:
            continue

        unit = (row.get("SATUAN") or "").strip()
        hasil_raw = row.get("HASIL ANALISA") or ""
        result = parse_result(hasil_raw)

        if in_class_split:
            bm_raw = row.get("BAKU MUTU Gol. I") or ""
        else:
            bm_raw = row.get("BAKU MUTU") or ""
        threshold = parse_threshold(bm_raw, param_id, param_dict)
        if param_dict.get(param_id, {}).get("no_threshold"):
            threshold = None
        if threshold is None and param_dict.get(param_id, {}).get("direction") == "qualitative":
            threshold = {"type": "qualitative", "expected": "Tidak Berbau"}

        qual = result.get("result") if result.get("qualitative") else None
        compliant = compute_compliant(
            result["result"] if not result.get("qualitative") else None,
            threshold,
            result["below_detection_limit"],
            qualitative_val=qual,
        )

        m = {
            "parameter_id": param_id,
            "parameter_label": param_label_raw,
            "category": param_dict.get(param_id, {}).get("category"),
            "unit": unit or param_dict.get(param_id, {}).get("unit"),
            "result": result["result"],
            "result_display": result["result_display"],
            "below_detection_limit": result["below_detection_limit"],
            "threshold": threshold,
            "compliant": compliant,
            "source_flagged_exceedance": result["source_flagged_exceedance"],
            "method": (row.get("ACUAN METODE") or "").strip() or None,
        }
        note = param_dict.get(param_id, {}).get("compliance_note")
        if note and result["source_flagged_exceedance"] and compliant:
            m["compliance_note"] = note

        if in_class_split:
            bm_raw_2 = row.get("BAKU MUTU Gol. II") or ""
            threshold_2 = parse_threshold(bm_raw_2, param_id, param_dict)
            m["threshold_gol_2"] = threshold_2
            m["compliant_gol_2"] = compute_compliant(
                result["result"] if not result.get("qualitative") else None,
                threshold_2,
                result["below_detection_limit"],
                qualitative_val=qual,
            )

        measurements.append(m)

    # Per-report summary
    total = len(measurements)
    compliant_count = sum(1 for x in measurements if x["compliant"] is True)
    non_compliant_count = sum(1 for x in measurements if x["compliant"] is False)
    non_compliant_params = [x["parameter_id"] for x in measurements if x["compliant"] is False]
    compliance_pct = round_to(compliant_count / total * 100, 2) if total else None

    sampling_date = _parse_date_id(header.get("Tanggal Pengambilan Sampel", ""))
    received_date = _parse_date_id(header.get("Tanggal Penerimaan Sampel", ""))
    testing = header.get("Tanggal Pengujian Sampel", "")
    testing_period = _parse_testing_period(testing)
    ambient = _extract_ambient_temp(lhu["param_table"])

    return {
        "report_no": lhu["report_no"],
        "order_no": header.get("No. Pesanan Pengujian"),
        "sample_code": header.get("Kode Sampel"),
        "sample_type": sample_type,
        "location_id": loc_id,
        "location_label_raw": raw_loc,
        "coordinates_dms": header.get("Titik Pengambilan Sampel"),
        "regulation_id": regulation_id,
        "regulation_raw": header.get("Acuan Baku Mutu"),
        "sampling_method": header.get("Metode Pengambilan Sampel"),
        "sampling_date": sampling_date,
        "received_date": received_date,
        "testing_period": testing_period,
        "report_date": "2025-10-08",
        "ambient_temp_c": ambient,
        "measurements": measurements,
        "summary": {
            "total_parameters": total,
            "compliant_count": compliant_count,
            "non_compliant_count": non_compliant_count,
            "non_compliant_parameters": non_compliant_params,
            "compliance_pct": compliance_pct,
        },
    }


def _extract_ambient_temp(param_table) -> int | None:
    return None  # Not in param table; stored in Catatan section. Default None.


def _parse_date_id(text: str) -> str | None:
    if not text:
        return None
    months = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
        "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }
    m = re.match(r"^\s*(\d{1,2})\s+(\w+)\s+(\d{4})", text)
    if not m:
        return None
    d, mon_word, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    mon = months.get(mon_word)
    if not mon:
        return None
    return f"{y:04d}-{mon:02d}-{d:02d}"


def _parse_testing_period(text: str) -> dict | None:
    if not text:
        return None
    # "10 September – 3 Oktober 2025"
    parts = re.split(r"\s*[–-]\s*", text, maxsplit=1)
    if len(parts) != 2:
        return None
    year_match = re.search(r"(\d{4})", parts[1])
    if not year_match:
        return None
    year = year_match.group(1)
    end_iso = _parse_date_id(parts[1])
    start_with_year = f"{parts[0]} {year}" if not re.search(r"\d{4}", parts[0]) else parts[0]
    start_iso = _parse_date_id(start_with_year)
    return {"start": start_iso, "end": end_iso}


def build_aggregate(reports: list[dict]) -> dict:
    by_type: dict[str, dict] = {}
    for r in reports:
        st = r["sample_type"]
        if st not in by_type:
            by_type[st] = {"reports": 0, "compliance_sum": 0.0, "exceedances": {}}
        by_type[st]["reports"] += 1
        if r["summary"]["compliance_pct"] is not None:
            by_type[st]["compliance_sum"] += r["summary"]["compliance_pct"]
        for p in r["summary"]["non_compliant_parameters"]:
            by_type[st]["exceedances"][p] = by_type[st]["exceedances"].get(p, 0) + 1
    result = {}
    for st, agg in by_type.items():
        n = agg["reports"]
        common = sorted(agg["exceedances"].items(), key=lambda kv: -kv[1])[:3]
        result[st] = {
            "reports": n,
            "compliance_pct_avg": round_to(agg["compliance_sum"] / n, 2) if n else None,
            "common_exceedances": [k for k, _ in common],
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json")
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_MD
    md_text = load_md(src)

    param_thresholds = read_json(RESOURCES_DIR / "parameter_thresholds.json")
    param_dict = param_thresholds["parameters"]
    parameter_dictionary = {
        pid: {k: v for k, v in pinfo.items() if k not in {"direction", "no_threshold", "compliance_note"}}
        for pid, pinfo in param_dict.items()
    }

    lhus = extract_lhu_sections(md_text)
    reports = [build_report(l, param_dict) for l in lhus]

    flags = [
        flag("info", "Tanda '^' di sumber LHU diterapkan ke parameter DO meski baku mutu DO bersifat minimum (≥4 mg/L). Field `compliant` di spec ini mengoreksi arah; `source_flagged_exceedance` mempertahankan tanda asli."),
        flag("warning", "Penomoran parameter Biologi pada LHU 7 dan LHU 8 mengandung typo (nomor 13 muncul dua kali). Spec ini menormalkan ulang nomor berurutan."),
    ]

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_MD],
        period={"start": "2025-09-10", "end": "2025-10-08"},
    )
    data["issuing_lab"] = {
        "name": "Laboratorium Ekologi PULIK CESS UNPAD",
        "accreditation": "KAN LP-1491-IDN",
        "address": "Jl. Sekeloa Selatan I Bandung 40132",
        "head": "Dr. Gemilang Lara Utama S., S.Pt., M.I.L",
    }
    data["data_quality_flags"] = flags
    data["parameter_dictionary"] = parameter_dictionary
    data["reports"] = reports
    data["aggregate_summary"] = {"by_sample_type": build_aggregate(reports)}

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    total_measurements = sum(len(r["measurements"]) for r in reports)
    print(f"[parse_{DATASET_ID}] wrote {target} ({len(reports)} reports, {total_measurements} measurements, {len(flags)} flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
