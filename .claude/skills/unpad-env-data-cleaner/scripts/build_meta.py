"""Build <out>/meta.json — dashboard-wide metadata."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import resolve_output, write_json

META = {
    "dashboard": {
        "title": "Dashboard Pemantauan Lingkungan UNPAD",
        "subtitle": "Pusat Pengembangan Kampus Berkelanjutan serta Keselamatan dan Keamanan Lingkungan (PKBKKL)",
        "organization": "Universitas Padjadjaran",
        "owner_email": "k.susanto@geophys.unpad.ac.id",
        "url": "https://dashboard-pk3l.unpad.ac.id",
        "version": "1.0",
        "last_updated": "2026-07-01"
    },
    "datasets": [
        {
            "id": "pengolahan_sampah",
            "label": "Pengolahan Sampah",
            "route": "/sampah/pengolahan",
            "icon": "recycle",
            "period_label": "Des 2025 – Jan 2026",
            "primary_kpi": {"label": "Total Sampah Diolah", "value_field": "total_processed_kg"}
        },
        {
            "id": "timbulan",
            "label": "Timbulan Sampah",
            "route": "/sampah/timbulan",
            "icon": "trash",
            "period_label": "Jan – Jun 2026",
            "primary_kpi": {"label": "Total Timbulan YTD", "value_field": "total_kg"}
        },
        {
            "id": "water_quality",
            "label": "Kualitas Air",
            "route": "/air",
            "icon": "droplet",
            "period_label": "Sep – Okt 2025",
            "primary_kpi": {"label": "Persentase Parameter Patuh", "value_field": "compliance_pct"}
        },
        {
            "id": "tree_incidents",
            "label": "Insiden Vegetasi",
            "route": "/vegetasi",
            "icon": "tree",
            "period_label": "2025",
            "primary_kpi": {"label": "Total Kejadian Pohon", "value_field": "total_events"}
        },
        {
            "id": "traffic_accidents",
            "label": "Kecelakaan Lalu Lintas",
            "route": "/lalu-lintas",
            "icon": "car-crash",
            "period_label": "Apr 2025 – Jun 2026",
            "primary_kpi": {"label": "Total Kecelakaan", "value_field": "total_cases"}
        },
        {
            "id": "b3_waste",
            "label": "Limbah B3",
            "route": "/limbah-b3",
            "icon": "flask",
            "period_label": "Sep 2024 – 2026",
            "primary_kpi": {"label": "Total Volume Limbah B3", "value_field": "total_volume_liter"}
        }
    ],
    "color_palette": {
        "organik": "#16a34a",
        "anorganik": "#2563eb",
        "residu": "#737373",
        "kompos": "#84cc16",
        "rdf": "#0891b2",
        "maggot": "#eab308",
        "dumping": "#ef4444",
        "compliant": "#16a34a",
        "exceedance": "#dc2626",
        "below_detection": "#94a3b8",
        "leaf": "#7ec43b",
        "forest": "#14532d",
        "organik_anorganik": "#64748b",
        "sisa_makanan": "#166534",
        "lingkungan": "#84cc16",
        "aset": "#a16207"
    }
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build data/meta.json.")
    ap.add_argument("--out", default=None, help="Output dir")
    args = ap.parse_args()

    out_dir = resolve_output(args.out)
    target = out_dir / "meta.json"
    write_json(target, META)
    print(f"[build_meta] wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
