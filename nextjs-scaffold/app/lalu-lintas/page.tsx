import { PageHeader } from "@/app/_components/PageHeader";
import { KpiCard } from "@/app/_components/KpiCard";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import { StackedBar } from "@/app/_components/Charts";
import { getLocations, getMeta, getTrafficAccidents } from "@/lib/data";
import { fmtInt } from "@/lib/format";
import { CarFront, Bike, Footprints, AlertTriangle } from "lucide-react";

const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export default async function LaluLintasPage() {
  const [meta, locations, data] = await Promise.all([getMeta(), getLocations(), getTrafficAccidents()]);

  const typeLabels = Object.fromEntries(data.vehicle_types.map((v) => [v.id, v.label]));

  function chartFor(year: number) {
    const yearData = data.yearly.find((y) => y.year === year);
    if (!yearData) return [];
    return MONTH_SHORT.map((m, i) => {
      const monthIso = `${year}-${String(i + 1).padStart(2, "0")}`;
      const row = yearData.monthly.find((mm) => mm.month === monthIso);
      const base: Record<string, any> = { bulan: m };
      for (const v of data.vehicle_types) {
        base[v.id] = row?.by_type[v.id] ?? 0;
      }
      return base;
    });
  }

  const palette = [
    meta.color_palette.exceedance,
    meta.color_palette.maggot,
    meta.color_palette.anorganik,
    meta.color_palette.organik,
    meta.color_palette.rdf,
    meta.color_palette.residu,
    meta.color_palette.dumping,
    meta.color_palette.kompos,
  ];

  const series = data.vehicle_types.map((v, i) => ({
    key: v.id,
    label: v.label,
    color: palette[i % palette.length],
  }));

  const y2025 = data.yearly.find((y) => y.year === 2025);
  const y2026 = data.yearly.find((y) => y.year === 2026);
  const tot2025 = y2025?.total_yearly_computed ?? 0;
  const tot2026 = y2026?.total_yearly_computed ?? 0;
  const beamCases = (y2025?.monthly.reduce((a, m) => a + (m.by_type.beam ?? 0) + (m.by_type.tabrak_2roda_beam ?? 0) + (m.by_type.tabrak_4roda_beam ?? 0), 0) ?? 0)
    + (y2026?.monthly.reduce((a, m) => a + (m.by_type.beam ?? 0) + (m.by_type.tabrak_2roda_beam ?? 0) + (m.by_type.tabrak_4roda_beam ?? 0), 0) ?? 0);

  return (
    <div>
      <PageHeader
        title="Kecelakaan Lalu Lintas"
        period={`${data.period.start} – ${data.period.end}`}
        description="Pencatatan kecelakaan di kawasan kampus UNPAD oleh Kantor Lingkungan. Mencakup kecelakaan tunggal, tabrakan antar pengguna jalan, serta insiden yang melibatkan armada sepeda listrik Beam. Data 2026 masih parsial (sampai April)."
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total 2025" value={fmtInt(tot2025)} unit="kasus" icon={CarFront} accent="red" />
        <KpiCard label="YTD 2026" value={fmtInt(tot2026)} unit="kasus" icon={AlertTriangle} accent="amber" />
        <KpiCard label="Kasus Melibatkan Beam" value={fmtInt(beamCases)} icon={Bike} accent="slate" />
        <KpiCard
          label="Pejalan Kaki"
          value={fmtInt(
            (y2025?.monthly.reduce((a, m) => a + (m.by_type.pejalan_kaki ?? 0), 0) ?? 0) +
              (y2026?.monthly.reduce((a, m) => a + (m.by_type.pejalan_kaki ?? 0), 0) ?? 0),
          )}
          icon={Footprints}
        />
      </section>

      <section className="card card-pad mt-8">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Distribusi Bulanan per Jenis (2025)</h3>
        <p className="text-xs text-ink-400 mb-4">
          September 2025 adalah puncak dengan 16 kasus, didominasi kecelakaan tunggal motor dan tabrakan roda dua.
        </p>
        <StackedBar data={chartFor(2025)} xKey="bulan" series={series} />
      </section>

      <section className="card card-pad mt-6">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Distribusi Bulanan per Jenis (2026, YTD)</h3>
        <p className="text-xs text-ink-400 mb-4">
          Data 2026 masih parsial (Jan – Apr). Total YTD: {tot2026} kasus.
        </p>
        <StackedBar data={chartFor(2026)} xKey="bulan" series={series} />
      </section>

      <section className="card overflow-hidden mt-8">
        <header className="px-5 py-4 border-b border-ink-200">
          <h3 className="text-sm font-semibold text-ink-900">Detail Kasus 2026 (Lokasi)</h3>
        </header>
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-600 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5">No</th>
              <th className="text-left px-4 py-2.5">Bulan</th>
              <th className="text-left px-4 py-2.5">Jenis</th>
              <th className="text-left px-4 py-2.5">Lokasi</th>
              <th className="text-right px-4 py-2.5">Jumlah</th>
              <th className="text-left px-4 py-2.5">Catatan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200">
            {data.incidents_detail_2026.map((it) => (
              <tr key={`${it.month}-${it.no}`}>
                <td className="px-4 py-2.5 tabular-nums text-ink-600">{it.no}</td>
                <td className="px-4 py-2.5 text-ink-600">{it.month}</td>
                <td className="px-4 py-2.5 text-ink-900">{typeLabels[it.type] ?? it.type}</td>
                <td className="px-4 py-2.5 text-ink-900">
                  {locations.locations[it.location_id]?.label ?? it.location_label_raw}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">{it.count}</td>
                <td className="px-4 py-2.5 text-xs text-ink-400">{it.note ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <DataQualityFlags flags={data.data_quality_flags} />
    </div>
  );
}
