"""Halaman: Tentang Data."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app_helpers import (
    configure_page,
    load_dataset,
    load_meta,
    load_shared,
    page_header,
    render_flags,
)

configure_page("Tentang Data")

meta = load_meta()
regulations = load_shared("regulations")["regulations"]
pengolahan = load_dataset("pengolahan_sampah")
timbulan = load_dataset("timbulan")
water = load_dataset("water_quality")
trees = load_dataset("tree_incidents")
traffic = load_dataset("traffic_accidents")

page_header(
    "Tentang Data",
    description=(
        "Halaman ini menjelaskan sumber, metodologi, dan catatan integritas seluruh data "
        "yang ditampilkan di dashboard."
    ),
)

# ─── Organisasi ────────────────────────────────────────────────────────

st.markdown("### Organisasi & Kontak")
st.markdown(
    f"""
Dashboard ini dikelola oleh **{meta['dashboard']['subtitle']}** di bawah
**{meta['dashboard']['organization']}**. Data berasal dari catatan operasional internal PKBKKL
dan laporan resmi pihak ketiga (Laboratorium Ekologi PULIK CESS UNPAD untuk uji air).

Kontak: {meta['dashboard']['owner_email']}
"""
)

st.divider()

# ─── Sumber per Domain ────────────────────────────────────────────────

st.markdown("### Sumber per Domain")

datasets = [
    ("Pengolahan Sampah", pengolahan),
    ("Timbulan Sampah", timbulan),
    ("Kualitas Air", water),
    ("Insiden Vegetasi", trees),
    ("Kecelakaan Lalu Lintas", traffic),
]
src_rows = []
for label, ds in datasets:
    src_rows.append({
        "Domain": label,
        "Periode": f"{ds['period']['start']} – {ds['period']['end']}",
        "File Sumber": ", ".join(ds["source_files"]),
        "Jumlah Flag": len(ds["data_quality_flags"]),
    })
st.dataframe(pd.DataFrame(src_rows), width='stretch', hide_index=True)

st.divider()

# ─── Baku Mutu ────────────────────────────────────────────────────────

st.markdown("### Acuan Baku Mutu")
for rid, r in regulations.items():
    with st.container(border=True):
        st.markdown(f"**{r['short_name']}**")
        st.caption(r["full_name"])
        st.markdown(r["scope"])

st.divider()

# ─── Metodologi ───────────────────────────────────────────────────────

st.markdown("### Metodologi & Konvensi Data")
st.markdown(
    """
- Semua massa sampah dalam **kilogram (kg)**; konsentrasi air dalam **mg/L** kecuali parameter
  biologi (JPT/100 ml atau CFU/100 ml).
- Tanggal mengikuti format ISO-8601 (`YYYY-MM-DD`). Beberapa tanggal di sheet harian
  Pengolahan Sampah diperbaiki dari serial Excel terbalik (M/D → D/M) dan ditandai di JSON
  dengan `date_corrected_from_md: true`.
- Tanda `^` di Laporan Hasil Uji menunjukkan nilai di atas baku mutu. Untuk parameter
  seperti **DO (oksigen terlarut)** yang baku mutunya bersifat _minimum_, status kepatuhan
  dihitung ulang dengan arah yang benar.
- Hasil di bawah limit deteksi (mis. `<0,016`) disimpan sebagai nilai limit dengan flag
  `below_detection_limit: true`.
- Notasi ilmiah (mis. `24 × 10⁷`) disimpan sebagai integer di JSON dan ditampilkan kembali
  ke notasi asli di UI.
- Entri yang ditandai **DIPERTANYAKAN** di sumber tidak dihitung dalam rata-rata.
- Validasi dilakukan oleh `scripts/validate.py` di skill `unpad-env-data-cleaner`.
"""
)

st.divider()

# ─── Pipeline & versi ─────────────────────────────────────────────────

st.markdown("### Pipeline Data")
st.markdown(
    """
```
Sumber MD/XLSX  →  Skill unpad-env-data-cleaner  →  data/*.json  →  Dashboard
   (manual)         (Python, deterministik)          (JSON tervalidasi)
```

Untuk regenerasi data:
```powershell
python .claude/skills/unpad-env-data-cleaner/scripts/run_all.py --out data
```
"""
)

st.divider()

# ─── Semua data quality flags terkumpul ──────────────────────────────

st.markdown("### Seluruh Catatan Integritas")
for label, ds in datasets:
    render_flags(ds["data_quality_flags"], title=f"Catatan: {label}")
