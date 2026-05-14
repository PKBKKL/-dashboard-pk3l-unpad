"""Halaman: Kualitas Air."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_helpers import (
    configure_page,
    fmt_pct,
    fmt_threshold,
    get_palette,
    load_dataset,
    load_shared,
    page_header,
    render_flags,
)

configure_page("Kualitas Air")

data = load_dataset("water_quality")
locations = load_shared("locations")["locations"]
regulations = load_shared("regulations")["regulations"]
palette = get_palette()

SAMPLE_TYPE_LABEL = {
    "air_permukaan": "Air Permukaan",
    "air_limbah": "Air Limbah",
    "air_sumur": "Air Sumur",
}

page_header(
    "Kualitas Air",
    period=f"Sampling {data['period']['start']} – {data['period']['end']}",
    description=(
        f"Sembilan Laporan Hasil Uji (LHU) dari <b>{data['issuing_lab']['name']}</b> "
        f"(akreditasi {data['issuing_lab']['accreditation']}). "
        "Status kepatuhan dihitung berdasarkan baku mutu masing-masing matriks. "
        "Parameter dengan tanda '^' di LHU asli yang bersifat minimum (mis. DO) "
        "telah dikoreksi arah perhitungannya."
    ),
)

# ─── KPI ──────────────────────────────────────────────────────────────────

total_params = sum(r["summary"]["total_parameters"] for r in data["reports"])
total_compliant = sum(r["summary"]["compliant_count"] for r in data["reports"])
total_non = sum(r["summary"]["non_compliant_count"] for r in data["reports"])
compliance_pct = (total_compliant / max(1, total_params)) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jumlah LHU", len(data["reports"]))
c2.metric("Parameter Patuh", total_compliant, delta=f"dari {total_params}", delta_color="off")
c3.metric("Parameter Tidak Patuh", total_non, delta_color="inverse")
c4.metric("Rasio Kepatuhan", fmt_pct(compliance_pct))

st.divider()

# ─── Bar: compliance per LHU ────────────────────────────────────────────

st.subheader("Kepatuhan per Titik Sampling")
st.caption(
    "Hijau = parameter patuh. Merah = di atas baku mutu. "
    "Parameter tanpa baku mutu eksplisit (Kesadahan, DHL, PO₄) tidak dihitung."
)

comp_rows = []
for r in data["reports"]:
    comp_rows.append({
        "Lokasi": r["location_label_raw"],
        "Patuh": r["summary"]["compliant_count"],
        "Tidak Patuh": r["summary"]["non_compliant_count"],
    })
df_comp = pd.DataFrame(comp_rows)
fig_comp = px.bar(
    df_comp, x="Lokasi", y=["Patuh", "Tidak Patuh"], barmode="group",
    color_discrete_map={"Patuh": palette["compliant"], "Tidak Patuh": palette["exceedance"]},
    height=380,
)
fig_comp.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title=None, xaxis_title=None)
fig_comp.update_xaxes(tickangle=-25)
st.plotly_chart(fig_comp, width='stretch')

st.divider()

# ─── Filter & detail per LHU ────────────────────────────────────────────

st.subheader("Detail per Laporan")

sample_types = sorted({r["sample_type"] for r in data["reports"]})
selected_types = st.multiselect(
    "Filter jenis sampel:",
    options=sample_types,
    default=sample_types,
    format_func=lambda s: SAMPLE_TYPE_LABEL.get(s, s),
)

filtered = [r for r in data["reports"] if r["sample_type"] in selected_types]

for r in filtered:
    loc = locations.get(r["location_id"] or "") or {}
    reg = regulations.get(r["regulation_id"] or "") or {}

    with st.container(border=True):
        cl, cr = st.columns([3, 1])
        with cl:
            st.markdown(
                f"**{r['location_label_raw']}** · "
                f"<span style='color:#475569;'>{SAMPLE_TYPE_LABEL.get(r['sample_type'], r['sample_type'])}</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"LHU {r['report_no']} · sampling {r['sampling_date']}"
                + (f" · {loc.get('lat'):.5f}, {loc.get('lon'):.5f}" if loc.get("lat") else "")
            )
            if reg:
                st.caption(f"Acuan: **{reg.get('short_name', '')}** — {reg.get('scope', '')}")
        with cr:
            st.metric("Kepatuhan", fmt_pct(r["summary"]["compliance_pct"]))

        # Detail parameter rows
        param_rows = []
        for m in r["measurements"]:
            if m["compliant"] is None:
                status = "Tanpa baku mutu"
            elif m["compliant"]:
                status = "Patuh (lab tanda ^)" if m["source_flagged_exceedance"] else "Patuh"
            else:
                status = "Di atas baku mutu"
            param_rows.append({
                "Parameter": m["parameter_label"],
                "Kategori": (m["category"] or "").capitalize(),
                "Hasil": m["result_display"] + (" (BDL)" if m["below_detection_limit"] else ""),
                "Satuan": m["unit"] or "",
                "Baku Mutu": fmt_threshold(m["threshold"]),
                "Status": status,
            })
        df_params = pd.DataFrame(param_rows)
        # Color status column
        def color_status(val: str) -> str:
            if "Di atas" in val:
                return "background-color: #fee2e2; color: #991b1b"
            if val == "Patuh":
                return "background-color: #dcfce7; color: #166534"
            if "Patuh (lab" in val:
                return "background-color: #fef3c7; color: #92400e"
            return "color: #94a3b8"

        styled = df_params.style.map(color_status, subset=["Status"])
        st.dataframe(styled, width='stretch', hide_index=True)

# ─── Map (lokasi sampling) ──────────────────────────────────────────────

st.divider()
st.subheader("Peta Titik Sampling")

map_rows = []
for r in filtered:
    loc = locations.get(r["location_id"] or "") or {}
    if loc.get("lat") and loc.get("lon"):
        map_rows.append({
            "lat": loc["lat"],
            "lon": loc["lon"],
            "Lokasi": r["location_label_raw"],
            "Jenis": SAMPLE_TYPE_LABEL.get(r["sample_type"], r["sample_type"]),
            "Kepatuhan (%)": r["summary"]["compliance_pct"] or 0,
        })
if map_rows:
    map_df = pd.DataFrame(map_rows)
    fig_map = px.scatter_map(
        map_df,
        lat="lat",
        lon="lon",
        hover_name="Lokasi",
        hover_data={"Jenis": True, "Kepatuhan (%)": ":.1f", "lat": False, "lon": False},
        color="Kepatuhan (%)",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        zoom=14,
        height=420,
        map_style="open-street-map",
    )
    fig_map.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_map, width='stretch')
else:
    st.info("Tidak ada titik sampling untuk filter yang dipilih.")

render_flags(data["data_quality_flags"])
