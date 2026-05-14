"""Halaman: Timbulan Sampah Harian."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_helpers import (
    MONTH_SHORT,
    configure_page,
    fmt_int,
    fmt_kg,
    fmt_month,
    fmt_num,
    get_palette,
    load_dataset,
    page_header,
    render_flags,
)

configure_page("Timbulan Sampah")

data = load_dataset("timbulan")
palette = get_palette()

page_header(
    "Timbulan Sampah",
    period=f"{data['period']['start']} – {data['period']['end']}",
    description=(
        "Jumlah sampah yang masuk ke pengelolaan UNPAD dari tujuh sumber kendaraan, "
        "indikator beban harian fasilitas. Pemisahan kategori Organik vs Anorganik+Residu "
        "dilakukan konsisten sejak April 2026 — bulan-bulan sebelumnya hanya total."
    ),
)

active = [m for m in data["monthly_summary"] if m["total_kg"]]

# ─── KPI ──────────────────────────────────────────────────────────────────

total_ytd = sum((m["total_kg"] or 0) for m in active)
total_active_days = sum(m["days_active"] for m in active)
avg_active = total_ytd / max(1, total_active_days)
peak = max(active, key=lambda m: m["total_kg"] or 0) if active else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total YTD", f"{fmt_int(total_ytd)} kg")
c2.metric("Bulan Aktif", len(active), help=f"{total_active_days} hari operasi")
c3.metric("Rata-rata / Hari Aktif", f"{fmt_int(avg_active)} kg")
c4.metric(
    "Bulan Puncak",
    fmt_month(peak["month"]).split(" ")[0] if peak else "—",
    delta=f"{fmt_int(peak['total_kg'])} kg" if peak else None,
    delta_color="off",
)

st.divider()

# ─── Two charts ─────────────────────────────────────────────────────────

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Timbulan Bulanan per Kategori")
    st.caption("Breakdown kategori hanya tersedia lengkap untuk April 2026.")
    rows = []
    for m in active:
        rows.append({
            "Bulan": MONTH_SHORT[int(m["month"].split("-")[1]) - 1],
            "Organik (Daun + Ranting)": m["organik_kg"],
            "Anorganik + Residu": m["anorganik_residu_kg"],
        })
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Bulan", y=["Organik (Daun + Ranting)", "Anorganik + Residu"],
        color_discrete_map={
            "Organik (Daun + Ranting)": palette["organik"],
            "Anorganik + Residu": palette["anorganik"],
        },
        labels={"value": "kg", "variable": ""},
        height=350,
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title=None, xaxis_title=None)
    st.plotly_chart(fig, width='stretch')

with col_r:
    st.subheader("Total vs Rata-rata Hari Aktif")
    st.caption("Garis biru: rata-rata per hari aktif (lebih representatif daripada total bulanan).")
    trend = pd.DataFrame([{
        "Bulan": MONTH_SHORT[int(m["month"].split("-")[1]) - 1],
        "Total (kg/bulan)": m["total_kg"] or 0,
        "Rata-rata (kg/hari aktif)": m["avg_kg_per_active_day"] or 0,
    } for m in active])
    fig2 = px.line(
        trend, x="Bulan", y=["Total (kg/bulan)", "Rata-rata (kg/hari aktif)"],
        color_discrete_map={
            "Total (kg/bulan)": palette["residu"],
            "Rata-rata (kg/hari aktif)": palette["anorganik"],
        },
        markers=True,
        height=350,
    )
    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title=None,
                       xaxis_title=None, yaxis_title="kg")
    st.plotly_chart(fig2, width='stretch')

st.divider()

# ─── Ringkasan tabel ────────────────────────────────────────────────────

st.subheader("Ringkasan Bulanan")
table = [{
    "Bulan": m["label"],
    "Total (kg)": m["total_kg"],
    "Hari Aktif": m["days_active"],
    "Avg/Hari Aktif (kg)": round(m["avg_kg_per_active_day"], 1) if m["avg_kg_per_active_day"] else None,
    "Organik (kg)": m["organik_kg"],
    "Anorganik+Residu (kg)": m["anorganik_residu_kg"],
    "Kategori Tersedia?": "Ya" if m["category_breakdown_available"] else "Total saja",
} for m in data["monthly_summary"]]
st.dataframe(pd.DataFrame(table), width='stretch', hide_index=True)

# ─── Sumber kendaraan ──────────────────────────────────────────────────

st.subheader("Sumber Kendaraan")
veh = pd.DataFrame([{
    "Kendaraan": v["label"],
    "Operator": v["operator"],
    "Tare (kg)": v.get("tare_kg"),
    "Catatan": v.get("note", ""),
} for v in data["vehicle_sources"]])
veh["Tare (kg)"] = veh["Tare (kg)"].astype("Int64")
st.dataframe(veh, width='stretch', hide_index=True)

# ─── Detail harian ─────────────────────────────────────────────────────

with st.expander("Lihat detail harian (interaktif)"):
    df_daily = pd.DataFrame([{
        "Tanggal": e["date"],
        "Hari": e["day_of_week"],
        "Total (kg)": e["total_kg"],
        "Catatan": e["note"] or "",
    } for e in data["daily_entries"] if e["total_kg"]])
    st.dataframe(df_daily, width='stretch', hide_index=True, height=300)

    fig_d = px.bar(df_daily, x="Tanggal", y="Total (kg)",
                   color_discrete_sequence=[palette["anorganik"]], height=300)
    fig_d.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_d, width='stretch')

render_flags(data["data_quality_flags"])
