import { PageHeader } from "@/app/_components/PageHeader";
import { KpiCard } from "@/app/_components/KpiCard";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import { StackedBar, LineSeries } from "@/app/_components/Charts";
import { getMeta, getTimbulan } from "@/lib/data";
import { fmtInt, fmtKg, fmtMonth, fmtNum } from "@/lib/format";
import { Trash2, Calendar, BarChart3 } from "lucide-react";

export default async function TimbulanPage() {
  const [meta, data] = await Promise.all([getMeta(), getTimbulan()]);
  const palette = meta.color_palette;

  const activeMonths = data.monthly_summary.filter((m) => m.total_kg && m.total_kg > 0);

  const monthlyData = activeMonths.map((m) => ({
    month: fmtMonth(m.month).split(" ")[0].slice(0, 3),
    organik: m.organik_kg,
    anorganik_residu: m.anorganik_residu_kg,
    total: m.total_kg ?? 0,
  }));

  const trendData = activeMonths.map((m) => ({
    month: fmtMonth(m.month).split(" ")[0].slice(0, 3),
    total: m.total_kg ?? 0,
    avg_aktif: m.avg_kg_per_active_day ?? 0,
  }));

  const totalYTD = activeMonths.reduce((a, m) => a + (m.total_kg ?? 0), 0);
  const totalActiveDays = activeMonths.reduce((a, m) => a + m.days_active, 0);
  const avgPerActiveDay = totalYTD / Math.max(1, totalActiveDays);
  const peakMonth = [...activeMonths].sort((a, b) => (b.total_kg ?? 0) - (a.total_kg ?? 0))[0];

  return (
    <div>
      <PageHeader
        title="Timbulan Sampah"
        period={`${data.period.start} – ${data.period.end}`}
        description="Jumlah sampah yang masuk ke pengelolaan UNPAD dari tujuh sumber kendaraan. Dipakai sebagai indikator beban harian fasilitas. Pemisahan kategori Organik vs Anorganik+Residu dilakukan konsisten sejak April 2026 — bulan-bulan sebelumnya hanya mencatat total."
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total YTD" value={fmtInt(Math.round(totalYTD))} unit="kg" icon={Trash2} />
        <KpiCard
          label="Bulan Aktif"
          value={fmtInt(activeMonths.length)}
          trend={`${totalActiveDays} hari operasi`}
          icon={Calendar}
        />
        <KpiCard
          label="Rata-rata per Hari Aktif"
          value={fmtInt(Math.round(avgPerActiveDay))}
          unit="kg/hari"
          accent="brand"
        />
        <KpiCard
          label="Bulan Puncak"
          value={fmtMonth(peakMonth?.month ?? "—").split(" ")[0]}
          unit={`${fmtInt(Math.round(peakMonth?.total_kg ?? 0))} kg`}
          icon={BarChart3}
          accent="amber"
        />
      </section>

      <section className="grid gap-6 mt-8 lg:grid-cols-2">
        <div className="card card-pad">
          <h3 className="text-sm font-semibold text-ink-900 mb-1">Timbulan Bulanan (Kategori)</h3>
          <p className="text-xs text-ink-400 mb-4">
            Hanya April 2026 yang memiliki breakdown kategori lengkap; bulan lain menunjukkan total saja.
          </p>
          <StackedBar
            data={monthlyData}
            xKey="month"
            series={[
              { key: "organik", label: "Organik (Daun + Ranting)", color: palette.organik },
              { key: "anorganik_residu", label: "Anorganik + Residu", color: palette.anorganik },
            ]}
            yLabel="kg"
          />
        </div>

        <div className="card card-pad">
          <h3 className="text-sm font-semibold text-ink-900 mb-1">Total vs Rata-rata Hari Aktif</h3>
          <p className="text-xs text-ink-400 mb-4">
            Garis biru: rata-rata per hari aktif. Lebih representatif daripada total bulanan karena jumlah hari
            operasi berbeda-beda.
          </p>
          <LineSeries
            data={trendData}
            xKey="month"
            series={[
              { key: "total", label: "Total (kg/bulan)", color: palette.residu },
              { key: "avg_aktif", label: "Rata-rata (kg/hari aktif)", color: palette.anorganik },
            ]}
          />
        </div>
      </section>

      <section className="card overflow-hidden mt-8">
        <header className="px-5 py-4 border-b border-ink-200">
          <h3 className="text-sm font-semibold text-ink-900">Ringkasan Bulanan</h3>
        </header>
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-600 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5">Bulan</th>
              <th className="text-right px-4 py-2.5">Total</th>
              <th className="text-right px-4 py-2.5">Hari Aktif</th>
              <th className="text-right px-4 py-2.5">Avg/Hari Aktif</th>
              <th className="text-right px-4 py-2.5">Organik</th>
              <th className="text-right px-4 py-2.5">Anorganik+Residu</th>
              <th className="text-left px-4 py-2.5">Kategori?</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200">
            {data.monthly_summary.map((m) => (
              <tr key={m.month}>
                <td className="px-4 py-2.5 font-medium text-ink-900">{m.label}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.total_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{m.days_active}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtNum(m.avg_kg_per_active_day)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.organik_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.anorganik_residu_kg)}</td>
                <td className="px-4 py-2.5 text-xs">
                  {m.category_breakdown_available ? (
                    <span className="text-brand-700">tersedia</span>
                  ) : (
                    <span className="text-ink-400">total saja</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-10">
        <h2 className="text-base font-semibold text-ink-900 mb-3">Sumber Kendaraan</h2>
        <div className="card card-pad">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-sm">
            {data.vehicle_sources.map((v) => (
              <div key={v.id} className="flex justify-between items-baseline border-b border-ink-100 pb-2">
                <div>
                  <div className="font-medium text-ink-900">{v.label}</div>
                  <div className="text-xs text-ink-400">{v.operator}{v.note ? ` · ${v.note}` : ""}</div>
                </div>
                {v.tare_kg && (
                  <div className="text-xs text-ink-600 tabular-nums">tare {fmtInt(v.tare_kg)} kg</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <DataQualityFlags flags={data.data_quality_flags} />
    </div>
  );
}
