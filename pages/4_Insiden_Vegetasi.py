"""Halaman: Insiden Vegetasi."""
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

configure_page("Insiden Vegetasi")

data = load_dataset("tree_incidents")
locations = load_shared("locations")["locations"]
palette = get_palette()

EVENT_LABELS = {
    "penebangan": "Penebangan",
    "pemangkasan": "Pemangkasan",
    "pohon_roboh": "Pohon Roboh",
    "pohon_patah": "Pohon Patah",
    "unspecified": "Tidak diketahui",
}

page_header(
    "Insiden Vegetasi",
    period=f"{data['period']['start']} – {data['period']['end']}",
    description=(
        "Rekapitulasi kegiatan pohon di seluruh kampus UNPAD Jatinangor sepanjang 2025. "
        "Mencakup kegiatan <b>terjadwal</b> (penebangan, pemangkasan) dan <b>insiden tak terencana</b> "
        "yang menjadi indikator manajemen risiko vegetasi (pohon roboh, pohon patah)."
    ),
)

# ─── KPI ──────────────────────────────────────────────────────────────────

yt = data["yearly_totals"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Kejadian", fmt_int(yt["total"]))
c2.metric("Penebangan", fmt_int(yt["penebangan"]))
c3.metric("Pemangkasan", fmt_int(yt["pemangkasan"]))
c4.metric(
    "Tak Terencana",
    fmt_int(yt["pohon_roboh"] + yt["pohon_patah"]),
    delta=f"{yt['pohon_roboh']} roboh + {yt['pohon_patah']} patah",
    delta_color="inverse",
)

st.divider()

# ─── Stacked bar: tren bulanan ─────────────────────────────────────────

st.subheader("Tren Bulanan per Jenis Kejadian")
st.caption(
    "Puncak Desember (13 kejadian) didominasi pohon patah (7) dan roboh (4). "
    "Juli juga tinggi dengan 4 pohon roboh."
)

monthly_rows = []
for m in data["monthly_totals"]:
    idx = int(m["month"].split("-")[1]) - 1
    monthly_rows.append({
        "Bulan": MONTH_SHORT[idx],
        "Penebangan": m["penebangan"],
        "Pemangkasan": m["pemangkasan"],
        "Pohon Roboh": m["pohon_roboh"],
        "Pohon Patah": m["pohon_patah"],
    })
df_m = pd.DataFrame(monthly_rows)

fig_m = px.bar(
    df_m, x="Bulan", y=["Penebangan", "Pemangkasan", "Pohon Roboh", "Pohon Patah"],
    color_discrete_map={
        "Penebangan": palette["residu"],
        "Pemangkasan": palette["organik"],
        "Pohon Roboh": palette["exceedance"],
        "Pohon Patah": palette["maggot"],
    },
    height=360,
)
fig_m.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title=None,
                    xaxis_title=None, yaxis_title="Jumlah Kejadian")
st.plotly_chart(fig_m, width='stretch')

st.divider()

# ─── Heatmap: lokasi × bulan ───────────────────────────────────────────

st.subheader("Distribusi Lokasi × Bulan")
st.caption("Lokasi diurutkan dari yang paling banyak kejadian.")

sorted_locs = sorted(data["incidents_by_location"], key=lambda l: -l["total"])
loc_labels = [locations.get(l["location_id"], {}).get("label", l["location_id"]) for l in sorted_locs]

heat_matrix = []
for l in sorted_locs:
    row = [0] * 12
    for mm in l["monthly"]:
        idx = int(mm["month"].split("-")[1]) - 1
        row[idx] = sum(ev["count"] for ev in mm["events"])
    heat_matrix.append(row)

fig_heat = px.imshow(
    heat_matrix,
    x=MONTH_SHORT,
    y=loc_labels,
    color_continuous_scale="Greens",
    aspect="auto",
    labels=dict(x="Bulan", y="Lokasi", color="Kejadian"),
    height=max(300, 28 * len(sorted_locs)),
    text_auto=True,
)
fig_heat.update_layout(margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig_heat, width='stretch')

st.divider()

# ─── Top lokasi ────────────────────────────────────────────────────────

st.subheader("Top Lokasi dengan Kejadian Terbanyak")

rows = []
for l in sorted_locs[:10]:
    events = {}
    for m in l["monthly"]:
        for e in m["events"]:
            events[e["type"]] = events.get(e["type"], 0) + e["count"]
    rincian = " · ".join(f"{EVENT_LABELS.get(k, k)}: {v}" for k, v in events.items())
    rows.append({
        "Lokasi": locations.get(l["location_id"], {}).get("label", l["location_id"]),
        "Total Kejadian": l["total"],
        "Rincian": rincian,
    })
st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

render_flags(data["data_quality_flags"])
