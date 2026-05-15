import { PageHeader } from "@/app/_components/PageHeader";
import { KpiCard } from "@/app/_components/KpiCard";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import { GroupedBar } from "@/app/_components/Charts";
import { getMeta, getRegulations, getLocations, getWaterQuality } from "@/lib/data";
import { fmtConcentration, fmtPct, thresholdLabel, cn } from "@/lib/format";
import { Droplet, ShieldCheck, ShieldAlert, FlaskConical } from "lucide-react";

const SAMPLE_TYPE_LABEL: Record<string, string> = {
  air_permukaan: "Air Permukaan",
  air_limbah: "Air Limbah",
  air_sumur: "Air Sumur",
};

export default async function AirPage() {
  const [meta, regulations, locations, data] = await Promise.all([
    getMeta(),
    getRegulations(),
    getLocations(),
    getWaterQuality(),
  ]);

  const totalParams = data.reports.reduce((a, r) => a + r.summary.total_parameters, 0);
  const totalCompliant = data.reports.reduce((a, r) => a + r.summary.compliant_count, 0);
  const totalNonCompliant = data.reports.reduce((a, r) => a + r.summary.non_compliant_count, 0);
  const compliancePct = (totalCompliant / Math.max(1, totalParams)) * 100;

  // Compliance per LHU (for grouped bar)
  const complianceChart = data.reports.map((r) => ({
    lhu: r.location_label_raw.length > 14 ? r.location_label_raw.slice(0, 14) + "…" : r.location_label_raw,
    patuh: r.summary.compliant_count,
    tidak: r.summary.non_compliant_count,
  }));

  return (
    <div>
      <PageHeader
        title="Kualitas Air"
        period={`Sampling ${data.period.start} – ${data.period.end}`}
        description={`Sembilan Laporan Hasil Uji (LHU) dari ${data.issuing_lab.name} (akreditasi ${data.issuing_lab.accreditation}). Mencakup enam titik air permukaan, dua titik air limbah, dan satu sumur pantau. Status kepatuhan dihitung berdasarkan baku mutu masing-masing matriks (PPRI 22/2021, Permen LH 5/2014, Permenkes 2/2023). Parameter dengan tanda "^" di LHU asli yang seharusnya bersifat minimum (mis. DO) telah dikoreksi arahnya.`}
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Jumlah LHU" value={String(data.reports.length)} icon={FlaskConical} />
        <KpiCard label="Parameter Patuh" value={String(totalCompliant)} unit={`dari ${totalParams}`} icon={ShieldCheck} accent="brand" />
        <KpiCard label="Parameter Tidak Patuh" value={String(totalNonCompliant)} icon={ShieldAlert} accent="red" />
        <KpiCard label="Rasio Kepatuhan" value={fmtPct(compliancePct)} icon={Droplet} accent="blue" />
      </section>

      <section className="card card-pad mt-8">
        <h3 className="text-sm font-semibold text-ink-900 mb-1">Kepatuhan per Titik Sampling</h3>
        <p className="text-xs text-ink-400 mb-4">
          Hijau = parameter patuh terhadap baku mutu. Merah = parameter di atas baku mutu. Parameter tanpa baku mutu
          eksplisit (Kesadahan, DHL, PO₄) tidak dihitung di salah satu sisi.
        </p>
        <GroupedBar
          data={complianceChart}
          xKey="lhu"
          series={[
            { key: "patuh", label: "Patuh", color: meta.color_palette.compliant },
            { key: "tidak", label: "Tidak Patuh", color: meta.color_palette.exceedance },
          ]}
        />
      </section>

      <section className="mt-10 space-y-6">
        <h2 className="text-base font-semibold text-ink-900">Detail Per Laporan</h2>
        {data.reports.map((r) => {
          const loc = r.location_id ? locations.locations[r.location_id] : null;
          const reg = r.regulation_id ? regulations.regulations[r.regulation_id] : null;
          return (
            <article key={r.report_no} className="card overflow-hidden">
              <header className="px-5 py-4 border-b border-ink-200 flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-ink-900">
                    {r.location_label_raw}
                    <span className="ml-2 text-xs text-ink-400 font-normal">{SAMPLE_TYPE_LABEL[r.sample_type]}</span>
                  </h3>
                  <div className="text-xs text-ink-400 mt-0.5">
                    LHU {r.report_no} · sampling {r.sampling_date}
                    {loc?.lat && loc?.lon && (
                      <> · {loc.lat.toFixed(5)}, {loc.lon.toFixed(5)}</>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-ink-400">Kepatuhan</div>
                  <div className="text-lg font-semibold tabular-nums text-ink-900">
                    {fmtPct(r.summary.compliance_pct)}
                  </div>
                </div>
              </header>

              {reg && (
                <div className="px-5 py-3 bg-ink-50 text-xs text-ink-600 border-b border-ink-200">
                  Acuan: <strong className="text-ink-900">{reg.short_name}</strong> · {reg.scope}
                </div>
              )}

              <table className="w-full text-xs">
                <thead className="bg-ink-50 text-ink-600 uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-4 py-2">Parameter</th>
                    <th className="text-left px-4 py-2">Kategori</th>
                    <th className="text-right px-4 py-2">Hasil</th>
                    <th className="text-right px-4 py-2">Baku Mutu</th>
                    <th className="text-center px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-200">
                  {r.measurements.map((m, i) => (
                    <tr key={`${r.report_no}-${i}`}>
                      <td className="px-4 py-2 text-ink-900">{m.parameter_label}</td>
                      <td className="px-4 py-2 text-ink-400 capitalize">{m.category ?? "—"}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-ink-900">
                        {m.result_display || fmtConcentration(m.result, m.unit)}
                        {m.below_detection_limit && (
                          <span className="ml-1 text-[10px] text-ink-400">(BDL)</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-ink-600">
                        {thresholdLabel(m.threshold as any)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <StatusPill compliant={m.compliant} sourceFlag={m.source_flagged_exceedance} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          );
        })}
      </section>

      <DataQualityFlags flags={data.data_quality_flags} />
    </div>
  );
}

function StatusPill({ compliant, sourceFlag }: { compliant: boolean | null; sourceFlag: boolean }) {
  if (compliant === null) {
    return <span className="text-[11px] text-ink-400">— tanpa baku mutu</span>;
  }
  if (compliant) {
    return (
      <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium",
        sourceFlag ? "bg-amber-50 text-amber-700" : "bg-green-50 text-green-700")}>
        {sourceFlag ? "Patuh (lab tanda ^)" : "Patuh"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-50 text-red-700">
      Di atas baku mutu
    </span>
  );
}
