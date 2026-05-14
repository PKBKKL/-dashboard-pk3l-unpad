import { PageHeader } from "@/app/_components/PageHeader";
import { KpiCard } from "@/app/_components/KpiCard";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import { HeatGrid, StackedBar } from "@/app/_components/Charts";
import { getLocations, getMeta, getTreeIncidents } from "@/lib/data";
import { fmtInt } from "@/lib/format";
import { Trees, Scissors, Wind, Hammer } from "lucide-react";

const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export default async function VegetasiPage() {
  const [meta, locations, data] = await Promise.all([getMeta(), getLocations(), getTreeIncidents()]);

  const monthlyBars = data.monthly_totals.map((m) => ({
    bulan: MONTH_SHORT[parseInt(m.month.split("-")[1], 10) - 1],
    penebangan: m.penebangan,
    pemangkasan: m.pemangkasan,
    pohon_roboh: m.pohon_roboh,
    pohon_patah: m.pohon_patah,
  }));

  // Heatmap rows = locations, cols = months
  const sortedLocs = [...data.incidents_by_location].sort((a, b) => b.total - a.total);
  const rowLabels = sortedLocs.map((l) => locations.locations[l.location_id]?.label ?? l.location_id);
  const heatValues = sortedLocs.map((l) =>
    MONTH_SHORT.map((_, idx) => {
      const targetMonth = `2025-${String(idx + 1).padStart(2, "0")}`;
      const month = l.monthly.find((mm) => mm.month === targetMonth);
      return month ? month.events.reduce((a, e) => a + e.count, 0) : 0;
    }),
  );

  const yt = data.yearly_totals;

  return (
    <div>
      <PageHeader
        title="Insiden Vegetasi"
        period="Januari – Desember 2025"
        description="Rekapitulasi kegiatan pohon di seluruh kampus UNPAD Jatinangor sepanjang 2025. Mencakup kegiatan terjadwal (penebangan, pemangkasan) dan insiden tak terencana yang menjadi indikator risiko (pohon roboh, pohon patah)."
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total Kejadian" value={fmtInt(yt.total)} icon={Trees} />
        <KpiCard label="Penebangan" value={fmtInt(yt.penebangan)} icon={Hammer} accent="slate" />
        <KpiCard label="Pemangkasan" value={fmtInt(yt.pemangkasan)} icon={Scissors} accent="brand" />
        <KpiCard
          label="Insiden Tak Terencana"
          value={fmtInt(yt.pohon_roboh + yt.pohon_patah)}
          unit={`${yt.pohon_roboh} roboh + ${yt.pohon_patah} patah`}
          icon={Wind}
          accent="red"
        />
      </section>

      <section className="card card-pad mt-8">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Tren Bulanan per Jenis Kejadian</h3>
        <p className="text-xs text-ink-400 mb-4">
          Puncak Desember (13 kejadian) didominasi oleh pohon patah (7) dan roboh (4). Juli juga tinggi dengan 4 pohon roboh.
        </p>
        <StackedBar
          data={monthlyBars}
          xKey="bulan"
          series={[
            { key: "penebangan", label: "Penebangan", color: meta.color_palette.residu },
            { key: "pemangkasan", label: "Pemangkasan", color: meta.color_palette.organik },
            { key: "pohon_roboh", label: "Pohon Roboh", color: meta.color_palette.exceedance },
            { key: "pohon_patah", label: "Pohon Patah", color: meta.color_palette.maggot },
          ]}
        />
      </section>

      <section className="card card-pad mt-6">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Distribusi per Lokasi & Bulan</h3>
        <p className="text-xs text-ink-400 mb-4">
          Lokasi diurutkan dari yang paling banyak kejadian. Intensitas warna menunjukkan jumlah kejadian per bulan.
        </p>
        <HeatGrid
          rows={rowLabels}
          cols={MONTH_SHORT}
          values={heatValues}
          baseColor="rgb(22, 163, 74)"
          rowLabel="Lokasi"
          colLabel="Bulan"
        />
      </section>

      <section className="card overflow-hidden mt-8">
        <header className="px-5 py-4 border-b border-ink-200">
          <h3 className="text-sm font-semibold text-ink-900">Top Lokasi dengan Kejadian Terbanyak</h3>
        </header>
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-600 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5">Lokasi</th>
              <th className="text-right px-4 py-2.5">Total</th>
              <th className="text-left px-4 py-2.5">Rincian</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200">
            {sortedLocs.slice(0, 10).map((l) => {
              const events: Record<string, number> = {};
              for (const m of l.monthly) {
                for (const e of m.events) {
                  events[e.type] = (events[e.type] ?? 0) + e.count;
                }
              }
              const eventLabels: Record<string, string> = {
                penebangan: "Penebangan", pemangkasan: "Pemangkasan",
                pohon_roboh: "Pohon Roboh", pohon_patah: "Pohon Patah",
                unspecified: "Tidak diketahui",
              };
              return (
                <tr key={l.location_id}>
                  <td className="px-4 py-2.5 font-medium text-ink-900">
                    {locations.locations[l.location_id]?.label ?? l.location_id}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{l.total}</td>
                  <td className="px-4 py-2.5 text-xs text-ink-600">
                    {Object.entries(events)
                      .map(([t, c]) => `${eventLabels[t] ?? t}: ${c}`)
                      .join(" · ")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <DataQualityFlags flags={data.data_quality_flags} />
    </div>
  );
}
