import { Recycle, Trash2, Droplet, Trees, CarFront, Leaf } from "lucide-react";
import { PageHeader } from "./_components/PageHeader";
import { KpiCard } from "./_components/KpiCard";
import {
  getMeta,
  getPengolahanSampah,
  getTimbulan,
  getWaterQuality,
  getTreeIncidents,
  getTrafficAccidents,
} from "@/lib/data";
import { fmtInt, fmtKg, fmtPct } from "@/lib/format";

export default async function OverviewPage() {
  const [meta, pengolahan, timbulan, water, trees, traffic] = await Promise.all([
    getMeta(),
    getPengolahanSampah(),
    getTimbulan(),
    getWaterQuality(),
    getTreeIncidents(),
    getTrafficAccidents(),
  ]);

  // Aggregate KPIs
  const totalProcessed = pengolahan.monthly_summary.reduce((a, m) => a + m.processed_kg, 0);
  const processingRate =
    pengolahan.monthly_summary.reduce((a, m) => a + m.processing_rate_pct, 0) /
    Math.max(1, pengolahan.monthly_summary.length);
  const totalTimbulan = timbulan.monthly_summary.reduce((a, m) => a + (m.total_kg ?? 0), 0);

  const waterReports = water.reports.length;
  const waterTotalParams = water.reports.reduce((a, r) => a + r.summary.total_parameters, 0);
  const waterCompliant = water.reports.reduce((a, r) => a + r.summary.compliant_count, 0);
  const waterCompliancePct = (waterCompliant / Math.max(1, waterTotalParams)) * 100;

  const treesTotal = trees.yearly_totals.total;
  const trafficTotal2025 = traffic.yearly[0]?.total_yearly_computed ?? 0;
  const trafficTotal2026 = traffic.yearly[1]?.total_yearly_computed ?? 0;

  return (
    <div>
      <PageHeader
        title={meta.dashboard.title}
        description={`Ringkasan kinerja lingkungan Universitas Padjadjaran dari lima domain pengawasan PK3L: pengolahan sampah, timbulan harian, kualitas air, insiden vegetasi, dan keselamatan lalu lintas kampus. Data diperbarui terakhir ${meta.dashboard.last_updated}.`}
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label="Sampah Diolah"
          value={fmtInt(Math.round(totalProcessed))}
          unit="kg total"
          trend={`Rata-rata ${fmtPct(processingRate)} dari total masuk`}
          icon={Recycle}
          accent="brand"
          href="/sampah/pengolahan"
        />
        <KpiCard
          label="Timbulan Sampah YTD"
          value={fmtInt(Math.round(totalTimbulan))}
          unit="kg"
          trend={`Dari ${timbulan.monthly_summary.filter((m) => m.total_kg).length} bulan aktif`}
          icon={Trash2}
          accent="slate"
          href="/sampah/timbulan"
        />
        <KpiCard
          label="Kepatuhan Parameter Air"
          value={fmtPct(waterCompliancePct)}
          trend={`${waterCompliant} dari ${waterTotalParams} parameter di ${waterReports} LHU`}
          icon={Droplet}
          accent="blue"
          href="/air"
        />
        <KpiCard
          label="Total Insiden Pohon 2025"
          value={fmtInt(treesTotal)}
          unit="kejadian"
          trend={`${trees.yearly_totals.pohon_roboh + trees.yearly_totals.pohon_patah} insiden tak terencana`}
          icon={Trees}
          accent="brand"
          href="/vegetasi"
        />
        <KpiCard
          label="Kecelakaan 2025"
          value={fmtInt(trafficTotal2025)}
          unit="kasus"
          trend={`${trafficTotal2026} kasus YTD 2026`}
          icon={CarFront}
          accent="red"
          href="/lalu-lintas"
        />
        <KpiCard
          label="Komposting + RDF + Maggot"
          value={fmtInt(
            Math.round(
              pengolahan.monthly_summary.reduce(
                (a, m) => a + m.output.kompos_kg + m.output.rdf_kg + m.output.maggot_kg,
                0,
              ),
            ),
          )}
          unit="kg hasil olahan"
          trend="Akumulasi Des 2025 – Jan 2026"
          icon={Leaf}
          accent="brand"
        />
      </section>

      <section className="mt-10">
        <h2 className="text-base font-semibold text-ink-900 mb-3">Penjelasan Singkat Data</h2>
        <div className="card card-pad space-y-4 text-sm text-ink-700 leading-relaxed">
          <p>
            <strong>Pengolahan Sampah.</strong> Catatan harian dari Tempat Pengelolaan Sampah PK3L UNPAD untuk dua
            bulan operasional (Desember 2025 dan Januari 2026). Sampah masuk dipilah menjadi tiga kategori (Organik,
            Anorganik, Residu) dan diolah dengan empat metode: <em>Kompos</em> untuk organik, <em>Bahan RDF</em>{" "}
            (Refuse-Derived Fuel) untuk anorganik, <em>Bubur Maggot</em> sebagai metode baru sejak Januari 2026, dan{" "}
            <em>Dumping</em> untuk residu yang tidak dapat diolah lebih lanjut.
          </p>
          <p>
            <strong>Timbulan Sampah.</strong> Jumlah sampah yang masuk ke pengelolaan UNPAD per hari, dipantau dari
            tujuh sumber kendaraan (Truk Tim Angsa, Truk IPDN, Pick Up, Viar, Cator, Mobil Traga, SOD RS). Pemisahan
            kategori Organik vs Anorganik+Residu mulai konsisten dilakukan pada April 2026.
          </p>
          <p>
            <strong>Kualitas Air.</strong> Sembilan Laporan Hasil Uji (LHU) dari Laboratorium Ekologi PULIK CESS UNPAD
            (KAN LP-1491-IDN) untuk sampling 10–12 September 2025: enam titik air permukaan, dua titik air limbah
            (IPAL Prodi Kimia & RS), dan satu sumur pantau. Acuan baku mutu sesuai PPRI 22/2021, Permen LH 5/2014,
            dan Permenkes 2/2023.
          </p>
          <p>
            <strong>Insiden Vegetasi.</strong> Rekapitulasi kegiatan dan kejadian pohon di seluruh kampus Jatinangor
            sepanjang 2025: penebangan dan pemangkasan terjadwal, serta insiden tak terencana (pohon roboh, pohon
            patah) yang menjadi indikator manajemen risiko vegetasi.
          </p>
          <p>
            <strong>Kecelakaan Lalu Lintas.</strong> Pencatatan kecelakaan di area kampus oleh Kantor Lingkungan, mencakup
            kecelakaan tunggal, tabrakan antar pengguna jalan, serta insiden yang melibatkan armada sepeda listrik
            Beam.
          </p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-base font-semibold text-ink-900 mb-3">Periode Data per Domain</h2>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-50 text-ink-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-2.5">Domain</th>
                <th className="text-left px-4 py-2.5">Periode</th>
                <th className="text-left px-4 py-2.5">Sumber Data</th>
                <th className="text-right px-4 py-2.5">Catatan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              {meta.datasets.map((d) => {
                const datasetMap: Record<string, { src: string; notes: number }> = {
                  pengolahan_sampah: { src: pengolahan.source_files[0], notes: pengolahan.data_quality_flags.length },
                  timbulan: { src: timbulan.source_files[0], notes: timbulan.data_quality_flags.length },
                  water_quality: { src: water.source_files[0], notes: water.data_quality_flags.length },
                  tree_incidents: { src: trees.source_files[0], notes: trees.data_quality_flags.length },
                  traffic_accidents: { src: traffic.source_files[0], notes: traffic.data_quality_flags.length },
                };
                const info = datasetMap[d.id];
                return (
                  <tr key={d.id}>
                    <td className="px-4 py-3 font-medium text-ink-900">{d.label}</td>
                    <td className="px-4 py-3 text-ink-600">{d.period_label}</td>
                    <td className="px-4 py-3 text-ink-600 text-xs">{info?.src ?? "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-ink-600">{info?.notes ?? 0}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
