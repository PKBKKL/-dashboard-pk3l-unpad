"""Dashboard Pemantauan Lingkungan UNPAD — Halaman Ringkasan."""
from __future__ import annotations

import streamlit as st

from app_helpers import (
    configure_page,
    fmt_int,
    fmt_pct,
    load_dataset,
    load_meta,
    page_header,
)

configure_page("Ringkasan")

meta = load_meta()
pengolahan = load_dataset("pengolahan_sampah")
timbulan = load_dataset("timbulan")
water = load_dataset("water_quality")
trees = load_dataset("tree_incidents")
traffic = load_dataset("traffic_accidents")

with st.sidebar:
    st.markdown(f"### {meta['dashboard']['organization']}")
    st.caption(meta["dashboard"]["subtitle"])
    st.caption(f"Versi {meta['dashboard']['version']} · diperbarui {meta['dashboard']['last_updated']}")

page_header(
    meta["dashboard"]["title"],
    description=(
        "Ringkasan kinerja lingkungan Universitas Padjadjaran dari lima domain pengawasan PK3L: "
        "pengolahan sampah, timbulan harian, kualitas air, insiden vegetasi, dan keselamatan lalu lintas kampus. "
        f"Data diperbarui terakhir {meta['dashboard']['last_updated']}."
    ),
)

# ─── KPI Row ─────────────────────────────────────────────────────────────

total_processed = sum(m["processed_kg"] for m in pengolahan["monthly_summary"])
avg_rate = sum(m["processing_rate_pct"] for m in pengolahan["monthly_summary"]) / max(
    1, len(pengolahan["monthly_summary"])
)
total_in = sum(m["incoming_kg"] for m in pengolahan["monthly_summary"])

total_timbulan = sum((m["total_kg"] or 0) for m in timbulan["monthly_summary"])
active_months = sum(1 for m in timbulan["monthly_summary"] if m["total_kg"])

water_total = sum(r["summary"]["total_parameters"] for r in water["reports"])
water_compliant = sum(r["summary"]["compliant_count"] for r in water["reports"])
water_compliance_pct = (water_compliant / max(1, water_total)) * 100

trees_total = trees["yearly_totals"]["total"]
trees_unplanned = trees["yearly_totals"]["pohon_roboh"] + trees["yearly_totals"]["pohon_patah"]

traffic_2025 = traffic["yearly"][0]["total_yearly_computed"]
traffic_2026 = traffic["yearly"][1]["total_yearly_computed"]

col1, col2, col3 = st.columns(3)
col1.metric(
    "Sampah Diolah",
    f"{fmt_int(total_processed)} kg",
    help=f"Akumulasi pengolahan {len(pengolahan['monthly_summary'])} bulan",
)
col2.metric(
    "Rasio Pengolahan",
    fmt_pct(avg_rate),
    help="Rata-rata persentase sampah masuk yang berhasil diolah",
)
col3.metric(
    "Timbulan YTD",
    f"{fmt_int(total_timbulan)} kg",
    help=f"Total dari {active_months} bulan aktif",
)

col4, col5, col6 = st.columns(3)
col4.metric(
    "Kepatuhan Parameter Air",
    fmt_pct(water_compliance_pct),
    help=f"{water_compliant} dari {water_total} parameter di {len(water['reports'])} LHU",
)
col5.metric(
    "Insiden Pohon (2025)",
    fmt_int(trees_total),
    delta=f"{trees_unplanned} tak terencana",
    delta_color="inverse",
)
col6.metric(
    "Kecelakaan",
    f"{fmt_int(traffic_2025)} (2025)",
    delta=f"{fmt_int(traffic_2026)} YTD 2026",
    delta_color="off",
)

st.divider()

# ─── Penjelasan Singkat ─────────────────────────────────────────────────

st.markdown("### Penjelasan Singkat Tiap Domain")

with st.expander("Pengolahan Sampah — komposisi & metode olahan", expanded=False):
    st.markdown(
        """
Catatan harian dari fasilitas Tempat Pengelolaan Sampah PK3L UNPAD untuk dua bulan operasional
(Desember 2025 dan Januari 2026). Sampah masuk dipilah menjadi tiga kategori (**Organik**,
**Anorganik**, **Residu**) dan diolah dengan empat metode:

- **Kompos** untuk organik
- **Bahan RDF** (Refuse-Derived Fuel) untuk anorganik
- **Bubur Maggot** sebagai metode baru sejak Januari 2026
- **Dumping** untuk residu yang tidak dapat diolah lebih lanjut
        """
    )

with st.expander("Timbulan Sampah — beban harian fasilitas", expanded=False):
    st.markdown(
        """
Jumlah sampah yang masuk ke pengelolaan UNPAD per hari, dipantau dari **tujuh sumber kendaraan**
(Truk Tim Angsa, Truk IPDN, Pick Up, Viar, Cator, Mobil Traga, SOD RS). Pemisahan kategori
Organik vs Anorganik+Residu mulai konsisten dilakukan pada April 2026; bulan sebelumnya
hanya mencatat total.
        """
    )

with st.expander("Kualitas Air — 9 LHU PULIK CESS UNPAD", expanded=False):
    st.markdown(
        f"""
Sembilan **Laporan Hasil Uji** (LHU) dari **{water['issuing_lab']['name']}**
(akreditasi {water['issuing_lab']['accreditation']}) untuk sampling 10–12 September 2025:

- 6 titik air permukaan (Sekebitung, Outlet Ciparanje, Embung, Inlet/Badan/Outlet Ekoriparian)
- 2 titik air limbah (IPAL Prodi Kimia & IPAL RS UNPAD)
- 1 sumur pantau

Acuan baku mutu: PPRI 22/2021 (air permukaan), Permen LH 5/2014 (air limbah),
Permenkes 2/2023 (air sumur).
        """
    )

with st.expander("Insiden Vegetasi — manajemen risiko pohon", expanded=False):
    st.markdown(
        """
Rekapitulasi kegiatan dan kejadian pohon di seluruh kampus Jatinangor sepanjang 2025.
Mencakup kegiatan **terjadwal** (penebangan, pemangkasan) dan **insiden tak terencana**
(pohon roboh, pohon patah). Rasio kegiatan tak terencana terhadap total menjadi indikator
manajemen risiko vegetasi kampus.
        """
    )

with st.expander("Kecelakaan Lalu Lintas — keselamatan kampus", expanded=False):
    st.markdown(
        """
Pencatatan kecelakaan di area kampus oleh Kantor Lingkungan. Mencakup kecelakaan tunggal,
tabrakan antar pengguna jalan, serta insiden yang melibatkan armada sepeda listrik **Beam**.
Data 2026 masih parsial (sampai April).
        """
    )

st.divider()

# ─── Periode per Domain ─────────────────────────────────────────────────

st.markdown("### Periode Data per Domain")

import pandas as pd  # noqa: E402

period_rows = []
for d in meta["datasets"]:
    ds_map = {
        "pengolahan_sampah": pengolahan,
        "timbulan": timbulan,
        "water_quality": water,
        "tree_incidents": trees,
        "traffic_accidents": traffic,
    }
    ds = ds_map.get(d["id"])
    period_rows.append({
        "Domain": d["label"],
        "Periode": d["period_label"],
        "Sumber": ds["source_files"][0] if ds else "—",
        "Catatan": len(ds["data_quality_flags"]) if ds else 0,
    })

st.dataframe(
    pd.DataFrame(period_rows),
    width='stretch',
    hide_index=True,
)

st.caption(
    f"Navigasi ke halaman detail di sidebar kiri. "
    f"Kontak: {meta['dashboard']['owner_email']}"
)
