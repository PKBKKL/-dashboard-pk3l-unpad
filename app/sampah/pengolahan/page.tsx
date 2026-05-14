import { PageHeader } from "@/app/_components/PageHeader";
import { KpiCard } from "@/app/_components/KpiCard";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import { StackedBar, GroupedBar, DonutChart } from "@/app/_components/Charts";
import { getMeta, getPengolahanSampah } from "@/lib/data";
import { fmtInt, fmtKg, fmtPct, fmtMonth } from "@/lib/format";
import { Recycle, ArrowDownToLine, Leaf } from "lucide-react";

export default async function PengolahanSampahPage() {
  const [meta, data] = await Promise.all([getMeta(), getPengolahanSampah()]);
  const palette = meta.color_palette;

  // Monthly stacked bar — incoming by category
  const monthlyBars = data.monthly_summary.map((m) => ({
    month: fmtMonth(m.month),
    organik: m.incoming_by_category_kg?.organik ?? 0,
    anorganik: m.incoming_by_category_kg?.anorganik ?? 0,
    residu: m.incoming_by_category_kg?.residu ?? 0,
  }));

  // Output methods donut (all months aggregated)
  const totalKompos = data.monthly_summary.reduce((a, m) => a + m.output.kompos_kg, 0);
  const totalRDF = data.monthly_summary.reduce((a, m) => a + m.output.rdf_kg, 0);
  const totalMaggot = data.monthly_summary.reduce((a, m) => a + m.output.maggot_kg, 0);
  const donutData = [
    { name: "Kompos", value: totalKompos, color: palette.kompos },
    { name: "Bahan RDF", value: totalRDF, color: palette.rdf },
    { name: "Bubur Maggot", value: totalMaggot, color: palette.maggot },
  ];

  // Monthly grouped: processed vs residual
  const flowData = data.monthly_summary.map((m) => ({
    month: fmtMonth(m.month),
    diolah: m.processed_kg,
    sisa: m.residual_kg,
  }));

  const totalIn = data.monthly_summary.reduce((a, m) => a + m.incoming_kg, 0);
  const totalOut = totalKompos + totalRDF + totalMaggot;
  const avgRate =
    data.monthly_summary.reduce((a, m) => a + m.processing_rate_pct, 0) /
    Math.max(1, data.monthly_summary.length);

  return (
    <div>
      <PageHeader
        title="Pengolahan Sampah"
        period={`${data.period.start} – ${data.period.end}`}
        description="Pencatatan harian sampah yang masuk ke fasilitas pengolahan PK3L UNPAD dan dilolah menjadi Kompos, Bahan RDF, atau Bubur Maggot. Sampah residu yang tidak dapat diolah dipindahkan ke area Dumping. Halaman ini memperlihatkan komposisi sampah masuk, efektivitas pengolahan, dan distribusi hasil olahan."
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total Sampah Masuk" value={fmtInt(Math.round(totalIn))} unit="kg" icon={ArrowDownToLine} />
        <KpiCard
          label="Total Diolah"
          value={fmtInt(Math.round(totalIn - data.monthly_summary.reduce((a, m) => a + m.residual_kg, 0)))}
          unit="kg"
          icon={Recycle}
          accent="brand"
        />
        <KpiCard label="Rasio Pengolahan" value={fmtPct(avgRate)} trend="Rata-rata bulanan" accent="brand" />
        <KpiCard label="Hasil Olahan" value={fmtInt(Math.round(totalOut))} unit="kg" icon={Leaf} accent="amber" />
      </section>

      <section className="grid gap-6 mt-8 lg:grid-cols-2">
        <div className="card card-pad">
          <h3 className="text-sm font-semibold text-ink-900 mb-1">Komposisi Sampah Masuk per Bulan</h3>
          <p className="text-xs text-ink-400 mb-4">
            Distribusi kategori (kg) — Organik mendominasi karena kontribusi besar dari daun & ranting taman.
          </p>
          <StackedBar
            data={monthlyBars}
            xKey="month"
            series={[
              { key: "organik", label: "Organik", color: palette.organik },
              { key: "anorganik", label: "Anorganik", color: palette.anorganik },
              { key: "residu", label: "Residu", color: palette.residu },
            ]}
            yLabel="kg"
          />
        </div>

        <div className="card card-pad">
          <h3 className="text-sm font-semibold text-ink-900 mb-1">Distribusi Hasil Olahan</h3>
          <p className="text-xs text-ink-400 mb-4">
            Total hasil olahan terakumulasi seluruh periode. Bubur Maggot adalah metode baru sejak Januari 2026.
          </p>
          <DonutChart data={donutData} />
        </div>
      </section>

      <section className="card card-pad mt-6">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Diolah vs Sisa (per Bulan)</h3>
        <p className="text-xs text-ink-400 mb-4">
          Sampah yang berhasil diolah dibanding yang berakhir di area Dumping. Selisih residu antar bulan
          mencerminkan komposisi sampah masuk dan kapasitas pengolahan.
        </p>
        <GroupedBar
          data={flowData}
          xKey="month"
          series={[
            { key: "diolah", label: "Diolah", color: palette.compliant },
            { key: "sisa", label: "Sisa (Residu)", color: palette.residu },
          ]}
        />
      </section>

      <section className="card overflow-hidden mt-8">
        <header className="px-5 py-4 border-b border-ink-200">
          <h3 className="text-sm font-semibold text-ink-900">Ringkasan Bulanan</h3>
        </header>
        <table className="w-full text-sm">
          <thead className="bg-ink-50 text-ink-600 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5">Bulan</th>
              <th className="text-right px-4 py-2.5">Masuk</th>
              <th className="text-right px-4 py-2.5">Diolah</th>
              <th className="text-right px-4 py-2.5">Sisa</th>
              <th className="text-right px-4 py-2.5">Kompos</th>
              <th className="text-right px-4 py-2.5">RDF</th>
              <th className="text-right px-4 py-2.5">Maggot</th>
              <th className="text-right px-4 py-2.5">Rasio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200">
            {data.monthly_summary.map((m) => (
              <tr key={m.month}>
                <td className="px-4 py-2.5 font-medium text-ink-900">{m.label}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.incoming_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.processed_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.residual_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.output.kompos_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.output.rdf_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{fmtKg(m.output.maggot_kg)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-brand-700 font-medium">
                  {fmtPct(m.processing_rate_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <DataQualityFlags flags={data.data_quality_flags} />
    </div>
  );
}
