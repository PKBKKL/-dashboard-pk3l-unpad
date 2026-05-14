"""Parse Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.md → tree_incidents.json.

Three tables in source:
  1. Rekapitulasi Jenis Kejadian per Bulan (event type × month)
  2. Rincian Kejadian per Lokasi Tahun 2025 (location × month, text cells like "1 Pohon roboh")
  3. Total Kejadian Pohon per Bulan
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md_parser import find_tables
from _utils import (
    RESOURCES_DIR,
    base_dataset,
    find_project_root,
    flag,
    load_md,
    parse_number,
    read_json,
    resolve_output,
    slugify,
    write_json,
)

SOURCE_MD = "Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.md"
DATASET_ID = "tree_incidents"

MONTHS_ID = [
    ("Januari", "2025-01"), ("Februari", "2025-02"), ("Maret", "2025-03"),
    ("April", "2025-04"), ("Mei", "2025-05"), ("Juni", "2025-06"),
    ("Juli", "2025-07"), ("Agustus", "2025-08"), ("September", "2025-09"),
    ("Oktober", "2025-10"), ("November", "2025-11"), ("Desember", "2025-12"),
]

EVENT_TYPE_LABEL_TO_ID = {
    "Penebangan Pohon": "penebangan",
    "Pemangkasan Pohon": "pemangkasan",
    "Pohon Roboh": "pohon_roboh",
    "Pohon Patah": "pohon_patah",
}

EVENT_TYPE_KEYWORD = {
    "penebangan": "penebangan",
    "pemangkasan": "pemangkasan",
    "roboh": "pohon_roboh",
    "patah": "pohon_patah",
}

LOCATION_LABEL_TO_ID = {
    "RSPTN": "rsptn", "FK": "fk", "FKG": "fkg", "Fapsi": "fapsi", "Fkep": "fkep",
    "FMIPA": "fmipa", "Fapet": "fapet", "Faperta": "faperta", "FTIP": "ftip",
    "FPIK": "fpik", "FTG": "ftg", "Farmasi": "farmasi", "PPBS": "ppbs",
    "Bale Santika": "bale-santika", "FEB": "feb", "FIKOM": "fikom", "FH": "fh",
    "FISIP": "fisip", "FIB": "fib", "Indomaret": "indomaret", "SC": "sc",
    "Lapangan Merah": "lapangan-merah", "Gor Jati": "gor-jati", "MRU": "mru",
    "Ciparanje": "ciparanje", "Rektorat": "rektorat", "Bale Wilasa": "bale-wilasa",
}


def parse_monthly_recap(md_text: str) -> list[dict]:
    """Parse 'Rekapitulasi Jenis Kejadian per Bulan'."""
    tables = find_tables(md_text, section_contains="Rekapitulasi Jenis Kejadian")
    if not tables:
        return []
    t = tables[0]
    # Index by month
    monthly: dict[str, dict[str, int]] = {iso: {"penebangan": 0, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 0} for _, iso in MONTHS_ID}
    for row in t.as_dicts():
        jenis = (row.get("Jenis Kejadian") or "").strip()
        ev_id = EVENT_TYPE_LABEL_TO_ID.get(jenis)
        if not ev_id:
            continue
        for name, iso in MONTHS_ID:
            n = parse_number(row.get(name)) or 0
            monthly[iso][ev_id] = int(n)
    # Build list with totals
    result = []
    for _, iso in MONTHS_ID:
        m = monthly[iso]
        m["total"] = m["penebangan"] + m["pemangkasan"] + m["pohon_roboh"] + m["pohon_patah"]
        result.append({"month": iso, **m})
    return result


def parse_location_table(md_text: str) -> tuple[list[dict], int]:
    """Parse 'Rincian Kejadian per Lokasi Tahun 2025' into incidents_by_location."""
    tables = find_tables(md_text, section_contains="Rincian Kejadian per Lokasi")
    if not tables:
        return [], 0
    t = tables[0]
    by_location: list[dict] = []
    unspecified_count = 0
    for row in t.as_dicts():
        loc_label = (row.get("Lokasi") or "").strip()
        if not loc_label:
            continue
        loc_id = LOCATION_LABEL_TO_ID.get(loc_label, slugify(loc_label))
        monthly_events: list[dict] = []
        for name, iso in MONTHS_ID:
            cell = (row.get(name) or "").strip()
            if not cell:
                continue
            # Try '1 Pohon roboh' or '2 Pemangkasan Pohon' etc.
            m = re.match(r"^\s*(\d+)\s+(.*?)\s*$", cell)
            if m:
                count, descr = int(m.group(1)), m.group(2).lower()
                ev_id = None
                for kw, eid in EVENT_TYPE_KEYWORD.items():
                    if kw in descr:
                        ev_id = eid
                        break
                if ev_id is None:
                    # Cell contained just a count without descriptor (e.g., Farmasi Oktober '1')
                    ev_id = "unspecified"
                    unspecified_count += count
                monthly_events.append({"month": iso, "events": [{"type": ev_id, "count": count}]})
            elif cell.isdigit():
                monthly_events.append({"month": iso, "events": [{"type": "unspecified", "count": int(cell)}]})
                unspecified_count += int(cell)
        if monthly_events:
            total = sum(ev["count"] for grp in monthly_events for ev in grp["events"])
            by_location.append({"location_id": loc_id, "monthly": monthly_events, "total": total})
    return by_location, unspecified_count


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Build {DATASET_ID}.json")
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    project = find_project_root()
    src = Path(args.source) if args.source else project / SOURCE_MD
    md_text = load_md(src)

    monthly_totals = parse_monthly_recap(md_text)
    by_loc, unspecified = parse_location_table(md_text)

    # Yearly totals
    yearly = {"penebangan": 0, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "unspecified": unspecified, "total": 0}
    for m in monthly_totals:
        for k in ("penebangan", "pemangkasan", "pohon_roboh", "pohon_patah"):
            yearly[k] += m[k]
    yearly["total"] = yearly["penebangan"] + yearly["pemangkasan"] + yearly["pohon_roboh"] + yearly["pohon_patah"] + yearly["unspecified"]

    flags = []
    if unspecified > 0:
        flags.append(flag("info", f"Terdapat {unspecified} kejadian tanpa keterangan jenis (mis. cell Farmasi Oktober '1'); ditandai 'unspecified'."))

    data = base_dataset(
        DATASET_ID,
        source_files=[SOURCE_MD],
        period={"start": "2025-01-01", "end": "2025-12-31"},
    )
    data["data_quality_flags"] = flags
    data["event_types"] = [
        {"id": "penebangan", "label": "Penebangan Pohon", "severity": "planned"},
        {"id": "pemangkasan", "label": "Pemangkasan Pohon", "severity": "planned"},
        {"id": "pohon_roboh", "label": "Pohon Roboh", "severity": "incident"},
        {"id": "pohon_patah", "label": "Pohon Patah", "severity": "incident"},
        {"id": "unspecified", "label": "Tidak diketahui", "severity": "unknown"},
    ]
    data["monthly_totals"] = monthly_totals
    data["yearly_totals"] = yearly
    data["incidents_by_location"] = by_loc

    out_dir = resolve_output(args.out)
    target = out_dir / f"{DATASET_ID}.json"
    write_json(target, data)
    print(f"[parse_{DATASET_ID}] wrote {target} ({len(by_loc)} locations, {yearly['total']} events, {len(flags)} flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
