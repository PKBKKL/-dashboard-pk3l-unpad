"""Halaman: Kecelakaan Lalu Lintas."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_helpers import (
    MONTH_SHORT,
    configure_page,
    fmt_int,
    get_palette,
    load_dataset,
    load_shared,
    page_header,
    render_flags,
)

configure_page("Kecelakaan Lalu Lintas")

data = load_dataset("traffic_accidents")
locations = load_shared("locations")["locations"]
palette = get_palette()

type_labels = {v["id"]: v["label"] for v in data["vehicle_types"]}

page_header(
    "Kecelakaan Lalu Lintas",
    period=f"{data['period']['start']} – {data['period']['end']}",
    description=(
        "Pencatatan kecelakaan di kawasan kampus UNPAD oleh Kantor Lingkungan. "
        "Mencakup kecelakaan tunggal, tabrakan antar pengguna jalan, serta insiden yang "
        "melibatkan armada sepeda listrik <b>Beam</b>. Tahun berjalan masih parsial."
    ),
)

# Tahun tidak dihafal: ambil apa adanya dari data.
by_year = {y["year"]: y for y in data["yearly"]}
years = sorted(by_year)
latest = years[-1] if years else None

def beam_count(y: dict | None) -> int:
    if not y:
        return 0
    return sum(
        (m["by_type"].get("beam", 0) + m["by_type"].get("tabrak_2roda_beam", 0)
         + m["by_type"].get("tabrak_4roda_beam", 0))
        for m in y["monthly"]
    )

def pedestrian_count(y: dict | None) -> int:
    if not y:
        return 0
    return sum(m["by_type"].get("pejalan_kaki", 0) for m in y["monthly"])


cols = st.columns(len(years) + 2)
for col, yr in zip(cols, years):
    label = f"YTD {yr}" if yr == latest and len(years) > 1 else f"Total {yr}"
    col.metric(label, fmt_int(by_year[yr]["total_yearly_computed"]))
cols[len(years)].metric("Melibatkan Beam", fmt_int(sum(beam_count(by_year[y]) for y in years)))
cols[len(years) + 1].metric("Pejalan Kaki", fmt_int(sum(pedestrian_count(by_year[y]) for y in years)))

st.divider()

# ─── Year selector ─────────────────────────────────────────────────────

year = st.radio(
    "Pilih tahun:",
    options=years,
    horizontal=True,
    index=0,
    label_visibility="collapsed",
)
selected = by_year[year]

# Build monthly data for selected year
rows = []
for i, label in enumerate(MONTH_SHORT, start=1):
    month_iso = f"{year}-{i:02d}"
    found = next((m for m in selected["monthly"] if m["month"] == month_iso), None)
    base = {"Bulan": label}
    for v in data["vehicle_types"]:
        base[v["label"]] = (found["by_type"].get(v["id"], 0) if found else 0)
    rows.append(base)
df_year = pd.DataFrame(rows)

cols_palette = [
    palette["exceedance"], palette["maggot"], palette["anorganik"],
    palette["organik"], palette["rdf"], palette["residu"],
    palette["dumping"], palette["kompos"],
]
color_map = {v["label"]: cols_palette[i % len(cols_palette)] for i, v in enumerate(data["vehicle_types"])}

st.subheader(f"Distribusi Bulanan per Jenis ({year})")
if year == latest and len(years) > 1:
    st.caption(f"Data {year} masih parsial (YTD: {selected['total_yearly_computed']} kasus).")
elif selected["monthly"]:
    peak = max(selected["monthly"], key=lambda m: m["total"])
    peak_label = MONTH_SHORT[int(peak["month"][-2:]) - 1]
    st.caption(f"{peak_label} {year} adalah puncak dengan {peak['total']} kasus.")
else:
    st.caption(f"Belum ada kasus tercatat pada {year}.")
fig = px.bar(
    df_year, x="Bulan",
    y=[v["label"] for v in data["vehicle_types"]],
    color_discrete_map=color_map,
    height=380,
)
fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title=None,
                  xaxis_title=None, yaxis_title="Jumlah Kasus")
st.plotly_chart(fig, width='stretch')

st.divider()

# ─── Detail per lokasi ────────────────────────────────────────────────
# spec 1.1 memakai `incidents_detail`; JSON lama (1.0) memakai `incidents_detail_2026`.

incidents = data.get("incidents_detail") or data.get("incidents_detail_2026") or []
if incidents:
    detail_years = sorted({it.get("year", int(str(it["month"])[:4])) for it in incidents})
    st.subheader(f"Detail Kasus {' & '.join(map(str, detail_years))} per Lokasi")
    detail_rows = []
    for it in incidents:
        loc_label = locations.get(it["location_id"], {}).get("label", it.get("location_label_raw", it["location_id"]))
        detail_rows.append({
            "No": it["no"],
            "Bulan": it["month"],
            "Jenis": type_labels.get(it["type"], it["type"]),
            "Lokasi": loc_label,
            "Jumlah": it["count"],
            "Catatan": it.get("note", ""),
        })
    st.dataframe(pd.DataFrame(detail_rows), width='stretch', hide_index=True)

# ─── Komparasi yearly ─────────────────────────────────────────────────

st.subheader("Komparasi Tahunan")
yearly_summary = []
for y in data["yearly"]:
    by_type = {}
    for m in y["monthly"]:
        for t, n in m["by_type"].items():
            by_type[t] = by_type.get(t, 0) + n
    for t_id, n in by_type.items():
        yearly_summary.append({
            "Tahun": str(y["year"]),
            "Jenis": type_labels.get(t_id, t_id),
            "Kasus": n,
        })
df_ys = pd.DataFrame(yearly_summary)
if not df_ys.empty:
    year_cycle = [palette["exceedance"], palette["anorganik"], palette["maggot"],
                  palette["organik"], palette["rdf"], palette["residu"]]
    fig_ys = px.bar(
        df_ys, x="Jenis", y="Kasus", color="Tahun", barmode="group",
        color_discrete_map={str(y): year_cycle[i % len(year_cycle)] for i, y in enumerate(years)},
        height=320,
    )
    fig_ys.update_layout(margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None)
    fig_ys.update_xaxes(tickangle=-15)
    st.plotly_chart(fig_ys, width='stretch')

render_flags(data["data_quality_flags"])
