"""Halaman: Pengolahan Sampah."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_helpers import (
    configure_page,
    fmt_int,
    fmt_kg,
    fmt_month,
    fmt_pct,
    get_palette,
    load_dataset,
    page_header,
    render_flags,
)

configure_page("Pengolahan Sampah")

data = load_dataset("pengolahan_sampah")
palette = get_palette()

page_header(
    "Pengolahan Sampah",
    period=f"{data['period']['start']} – {data['period']['end']}",
    description=(
        "Pencatatan harian sampah yang masuk ke fasilitas pengolahan PK3L UNPAD dan diolah "
        "menjadi <b>Kompos</b>, <b>Bahan RDF</b>, atau <b>Bubur Maggot</b>. Sampah residu "
        "yang tidak dapat diolah dipindahkan ke area <b>Dumping</b>. Halaman ini memperlihatkan "
        "komposisi sampah masuk, efektivitas pengolahan, dan distribusi hasil olahan."
    ),
)

# ─── KPI ──────────────────────────────────────────────────────────────────

total_in = sum(m["incoming_kg"] for m in data["monthly_summary"])
total_processed = sum(m["processed_kg"] for m in data["monthly_summary"])
total_residual = sum(m["residual_kg"] for m in data["monthly_summary"])
total_kompos = sum(m["output"]["kompos_kg"] for m in data["monthly_summary"])
total_rdf = sum(m["output"]["rdf_kg"] for m in data["monthly_summary"])
total_maggot = sum(m["output"]["maggot_kg"] for m in data["monthly_summary"])
total_output = total_kompos + total_rdf + total_maggot
avg_rate = sum(m["processing_rate_pct"] for m in data["monthly_summary"]) / max(1, len(data["monthly_summary"]))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sampah Masuk", f"{fmt_int(total_in)} kg")
c2.metric("Total Diolah", f"{fmt_int(total_processed)} kg", help=f"Sisa residu: {fmt_int(total_residual)} kg")
c3.metric("Rasio Pengolahan", fmt_pct(avg_rate))
c4.metric("Total Hasil Olahan", f"{fmt_int(total_output)} kg")

st.divider()

# ─── Komposisi bulanan ──────────────────────────────────────────────────

st.subheader("Komposisi Sampah Masuk per Bulan")
st.caption("Distribusi kategori per bulan. Organik mendominasi karena kontribusi daun & ranting taman.")

comp_rows = []
for m in data["monthly_summary"]:
    cat = m.get("incoming_by_category_kg") or {}
    comp_rows.append({
        "Bulan": fmt_month(m["month"]),
        "Organik": cat.get("organik", 0),
        "Anorganik": cat.get("anorganik", 0),
        "Residu": cat.get("residu", 0),
    })
df_comp = pd.DataFrame(comp_rows)

fig_comp = px.bar(
    df_comp,
    x="Bulan",
    y=["Organik", "Anorganik", "Residu"],
    color_discrete_map={
        "Organik": palette["organik"],
        "Anorganik": palette["anorganik"],
        "Residu": palette["residu"],
    },
    labels={"value": "kg", "variable": "Kategori"},
    height=380,
)
fig_comp.update_layout(legend_title=None, xaxis_title=None, margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig_comp, width='stretch')

# ─── Two charts side-by-side ────────────────────────────────────────────

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Distribusi Hasil Olahan")
    st.caption("Akumulasi seluruh periode. Bubur Maggot baru muncul Januari 2026.")
    df_donut = pd.DataFrame({
        "Metode": ["Kompos", "Bahan RDF", "Bubur Maggot"],
        "kg": [total_kompos, total_rdf, total_maggot],
    })
    fig_donut = px.pie(
        df_donut, names="Metode", values="kg", hole=0.5,
        color="Metode",
        color_discrete_map={
            "Kompos": palette["kompos"],
            "Bahan RDF": palette["rdf"],
            "Bubur Maggot": palette["maggot"],
        },
        height=350,
    )
    fig_donut.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_donut, width='stretch')

with col_r:
    st.subheader("Diolah vs Sisa per Bulan")
    st.caption("Selisih residu antar bulan mencerminkan komposisi dan kapasitas pengolahan.")
    flow_rows = [{
        "Bulan": fmt_month(m["month"]),
        "Diolah": m["processed_kg"],
        "Sisa (Residu)": m["residual_kg"],
    } for m in data["monthly_summary"]]
    df_flow = pd.DataFrame(flow_rows)
    fig_flow = px.bar(
        df_flow, x="Bulan", y=["Diolah", "Sisa (Residu)"],
        barmode="group",
        color_discrete_map={
            "Diolah": palette["compliant"],
            "Sisa (Residu)": palette["residu"],
        },
        height=350,
    )
    fig_flow.update_layout(legend_title=None, xaxis_title=None, yaxis_title="kg",
                            margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_flow, width='stretch')

st.divider()

# ─── Tabel ringkasan bulanan ─────────────────────────────────────────────

st.subheader("Ringkasan Bulanan")
table_rows = [{
    "Bulan": m["label"],
    "Masuk (kg)": m["incoming_kg"],
    "Diolah (kg)": m["processed_kg"],
    "Sisa (kg)": m["residual_kg"],
    "Kompos (kg)": m["output"]["kompos_kg"],
    "RDF (kg)": m["output"]["rdf_kg"],
    "Maggot (kg)": m["output"]["maggot_kg"],
    "Rasio (%)": round(m["processing_rate_pct"], 1),
} for m in data["monthly_summary"]]
st.dataframe(pd.DataFrame(table_rows), width='stretch', hide_index=True)

# ─── Time series harian (opsional, interaktif) ──────────────────────────

with st.expander("Lihat detail harian"):
    daily_rows = []
    for e in data["daily_entries"]:
        daily_rows.append({
            "Tanggal": e["date"],
            "Masuk (kg)": e["totals"]["incoming_kg"],
            "Diolah (kg)": e["totals"]["processed_kg"],
            "Sisa (kg)": e["totals"]["residual_kg"],
            "Tgl Dikoreksi": "Ya" if e.get("date_corrected_from_md") else "",
        })
    df_daily = pd.DataFrame(daily_rows).sort_values("Tanggal")
    st.dataframe(df_daily, width='stretch', hide_index=True, height=300)

    fig_daily = px.line(
        df_daily, x="Tanggal", y=["Masuk (kg)", "Diolah (kg)"],
        color_discrete_map={
            "Masuk (kg)": palette["residu"],
            "Diolah (kg)": palette["compliant"],
        },
        height=280,
    )
    fig_daily.update_layout(legend_title=None, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_daily, width='stretch')

render_flags(data["data_quality_flags"])
