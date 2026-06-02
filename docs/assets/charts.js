// Plotly chart wrappers — match Streamlit version visually.
// Assumes Plotly is loaded globally via CDN <script src="plotly.min.js">.

const PLOTLY_CONFIG = {
  responsive: true,
  displayModeBar: false,
  locale: "id",
};

const LAYOUT_BASE = {
  margin: { t: 10, b: 40, l: 50, r: 10 },
  font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#475569" },
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  xaxis: { gridcolor: "#e2e8f0", linecolor: "#cbd5e1" },
  yaxis: { gridcolor: "#e2e8f0", linecolor: "#cbd5e1" },
  legend: { font: { size: 11 } },
  hoverlabel: { bgcolor: "white", bordercolor: "#e2e8f0", font: { size: 12, color: "#0f172a" } },
};

function mergeLayout(extra) {
  return {
    ...LAYOUT_BASE,
    ...extra,
    margin: { ...LAYOUT_BASE.margin, ...(extra?.margin ?? {}) },
    xaxis: { ...LAYOUT_BASE.xaxis, ...(extra?.xaxis ?? {}) },
    yaxis: { ...LAYOUT_BASE.yaxis, ...(extra?.yaxis ?? {}) },
  };
}

export function stackedBar(containerId, { x, series, yLabel, height = 360 }) {
  const traces = series.map((s) => ({
    x,
    y: s.y,
    name: s.label,
    type: "bar",
    marker: { color: s.color },
  }));
  Plotly.newPlot(
    containerId,
    traces,
    mergeLayout({
      barmode: "stack",
      height,
      yaxis: { title: yLabel ?? "" },
    }),
    PLOTLY_CONFIG,
  );
}

export function groupedBar(containerId, { x, series, yLabel, height = 360 }) {
  const traces = series.map((s) => ({
    x,
    y: s.y,
    name: s.label,
    type: "bar",
    marker: { color: s.color },
  }));
  Plotly.newPlot(
    containerId,
    traces,
    mergeLayout({
      barmode: "group",
      height,
      yaxis: { title: yLabel ?? "" },
    }),
    PLOTLY_CONFIG,
  );
}

export function lineChart(containerId, { x, series, yLabel, height = 320 }) {
  const traces = series.map((s) => ({
    x,
    y: s.y,
    name: s.label,
    type: "scatter",
    mode: "lines+markers",
    line: { color: s.color, width: 2 },
    marker: { size: 6 },
  }));
  Plotly.newPlot(
    containerId,
    traces,
    mergeLayout({ height, yaxis: { title: yLabel ?? "" } }),
    PLOTLY_CONFIG,
  );
}

export function donutChart(containerId, { labels, values, colors, height = 320 }) {
  const trace = {
    labels,
    values,
    type: "pie",
    hole: 0.5,
    marker: { colors },
    textinfo: "percent",
    hovertemplate: "%{label}: %{value:,.0f} (%{percent})<extra></extra>",
  };
  Plotly.newPlot(containerId, [trace], mergeLayout({ height }), PLOTLY_CONFIG);
}

export function heatmap(containerId, { x, y, z, height = 360, colorscale = "Greens" }) {
  const trace = {
    x, y, z,
    type: "heatmap",
    colorscale,
    showscale: true,
    hovertemplate: "%{y} · %{x}: %{z}<extra></extra>",
  };
  Plotly.newPlot(
    containerId,
    [trace],
    mergeLayout({
      height,
      xaxis: { side: "top" },
      yaxis: { autorange: "reversed" },
    }),
    PLOTLY_CONFIG,
  );
}

export function treemap(containerId, { labels, parents, values, text, customColors, height = 380 }) {
  const trace = {
    type: "treemap",
    labels,
    parents: parents ?? labels.map(() => ""),
    values,
    text: text ?? labels.map((_, i) => ""),
    textinfo: "label+text+value",
    hovertemplate: "<b>%{label}</b><br>%{text}<br>%{value} (%{percentRoot:.1%})<extra></extra>",
    marker: customColors ? { colors: customColors } : { colorscale: [[0, "#dcfce7"], [0.5, "#65a30d"], [1, "#14532d"]] },
    pathbar: { visible: false },
    tiling: { packing: "squarify" },
  };
  Plotly.newPlot(
    containerId,
    [trace],
    mergeLayout({ height, margin: { t: 10, b: 10, l: 10, r: 10 } }),
    PLOTLY_CONFIG,
  );
}

export function dailyBar(containerId, { x, y, color, name, height = 280 }) {
  const trace = {
    x,
    y,
    type: "bar",
    name,
    marker: { color },
  };
  Plotly.newPlot(containerId, [trace], mergeLayout({ height }), PLOTLY_CONFIG);
}
