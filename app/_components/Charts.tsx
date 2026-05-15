"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const TOOLTIP_STYLE = {
  contentStyle: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: "#0f172a", fontWeight: 600 },
};

export type Series = { key: string; label: string; color: string };

export function StackedBar({
  data,
  series,
  xKey,
  height = 320,
  yLabel,
}: {
  data: any[];
  series: Series[];
  xKey: string;
  height?: number;
  yLabel?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 12, fill: "#475569" }}
          axisLine={false}
          tickLine={false}
          label={yLabel ? { value: yLabel, angle: -90, position: "insideLeft", fontSize: 12, fill: "#94a3b8" } : undefined}
        />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} stackId="x" name={s.label} fill={s.color} radius={[0, 0, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function GroupedBar({
  data,
  series,
  xKey,
  height = 320,
}: {
  data: any[];
  series: Series[];
  xKey: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LineSeries({
  data,
  series,
  xKey,
  height = 280,
}: {
  data: any[];
  series: Series[];
  xKey: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            name={s.label}
            stroke={s.color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({
  data,
  height = 240,
}: {
  data: { name: string; value: number; color: string }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="value" innerRadius={55} outerRadius={90} paddingAngle={1}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color} />
          ))}
        </Pie>
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} verticalAlign="bottom" />
      </PieChart>
    </ResponsiveContainer>
  );
}

// Simple heatmap as CSS grid — better than ad-hoc Recharts hack
export function HeatGrid({
  rows,
  cols,
  values,
  maxValue,
  baseColor = "rgb(22, 163, 74)",
  rowLabel = "",
  colLabel = "",
  cellLabel,
}: {
  rows: string[];
  cols: string[];
  values: number[][];
  maxValue?: number;
  baseColor?: string;
  rowLabel?: string;
  colLabel?: string;
  cellLabel?: (v: number, row: string, col: string) => string;
}) {
  const max = maxValue ?? Math.max(1, ...values.flat());
  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-0 text-xs">
        <thead>
          <tr>
            <th className="text-ink-400 font-normal text-left pr-2 pb-1">
              {rowLabel} {colLabel && `\\ ${colLabel}`}
            </th>
            {cols.map((c) => (
              <th key={c} className="text-ink-600 font-normal px-1 pb-1 min-w-[40px]">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={r}>
              <td className="text-ink-600 pr-2 py-1 whitespace-nowrap">{r}</td>
              {cols.map((c, ci) => {
                const v = values[ri]?.[ci] ?? 0;
                const intensity = max > 0 ? v / max : 0;
                const bg =
                  intensity === 0
                    ? "#f8fafc"
                    : `color-mix(in srgb, ${baseColor} ${Math.round(intensity * 100)}%, white)`;
                const color = intensity > 0.55 ? "white" : "#0f172a";
                return (
                  <td
                    key={c}
                    title={cellLabel ? cellLabel(v, r, c) : `${r} · ${c}: ${v}`}
                    className="text-center px-1 py-1 tabular-nums rounded"
                    style={{ background: bg, color, minWidth: 36 }}
                  >
                    {v || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
