import { PageHeader } from "@/app/_components/PageHeader";
import { DataQualityFlags } from "@/app/_components/DataQualityFlag";
import {
  getMeta,
  getPengolahanSampah,
  getRegulations,
  getTimbulan,
  getTrafficAccidents,
  getTreeIncidents,
  getWaterQuality,
} from "@/lib/data";

export default async function TentangPage() {
  const [meta, regulations, pengolahan, timbulan, water, trees, traffic] = await Promise.all([
    getMeta(),
    getRegulations(),
    getPengolahanSampah(),
    getTimbulan(),
    getWaterQuality(),
    getTreeIncidents(),
    getTrafficAccidents(),
  ]);

  const datasets = [
    { ds: pengolahan, label: "Pengolahan Sampah" },
    { ds: timbulan, label: "Timbulan Sampah" },
    { ds: water, label: "Kualitas Air" },
    { ds: trees, label: "Insiden Vegetasi" },
    { ds: traffic, label: "Kecelakaan Lalu Lintas" },
  ];

  return (
    <div>
      <PageHeader
        title="Tentang Data"
        description="Halaman ini menjelaskan sumber, metodologi, dan catatan integritas seluruh data yang ditampilkan di dashboard."
      />

      <section className="card card-pad space-y-3 text-sm text-ink-700 leading-relaxed">
        <h2 className="text-base font-semibold text-ink-900">Organisasi & Tanggung Jawab</h2>
        <p>
          Dashboard ini dikelola oleh <strong>{meta.dashboard.subtitle}</strong> (PK3L) di bawah{" "}
          <strong>{meta.dashboard.organization}</strong>. Data berasal dari catatan operasional internal PK3L
          dan dari laporan resmi pihak ketiga (Laboratorium Ekologi PULIK CESS UNPAD untuk uji air).
        </p>
        <p>
          Kontak: <a className="text-brand-700 underline" href={`mailto:${meta.dashboard.owner_email}`}>{meta.dashboard.owner_email}</a>
        </p>
      </section>

      <section className="card card-pad mt-6">
        <h2 className="text-base font-semibold text-ink-900 mb-3">Sumber per Domain</h2>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-ink-400 border-b border-ink-200">
            <tr>
              <th className="text-left py-2 pr-4">Domain</th>
              <th className="text-left py-2 pr-4">Periode</th>
              <th className="text-left py-2 pr-4">File Sumber</th>
              <th className="text-left py-2">Catatan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200">
            {datasets.map(({ ds, label }) => (
              <tr key={ds.dataset_id}>
                <td className="py-3 pr-4 font-medium text-ink-900">{label}</td>
                <td className="py-3 pr-4 text-ink-600">
                  {ds.period.start} – {ds.period.end}
                </td>
                <td className="py-3 pr-4 text-xs text-ink-600">{ds.source_files.join(", ")}</td>
                <td className="py-3 tabular-nums text-ink-600">{ds.data_quality_flags.length} flag</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card card-pad mt-6">
        <h2 className="text-base font-semibold text-ink-900 mb-3">Acuan Baku Mutu</h2>
        <div className="space-y-3 text-sm">
          {Object.entries(regulations.regulations).map(([id, r]) => (
            <div key={id} className="border-b border-ink-100 pb-3 last:border-0 last:pb-0">
              <div className="font-medium text-ink-900">{r.short_name}</div>
              <div className="text-xs text-ink-400">{r.full_name}</div>
              <div className="text-xs text-ink-600 mt-1">{r.scope}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="card card-pad mt-6 text-sm leading-relaxed text-ink-700">
        <h2 className="text-base font-semibold text-ink-900 mb-2">Metodologi & Konvensi Data</h2>
        <ul className="list-disc pl-5 space-y-1.5">
          <li>Semua massa sampah dalam <strong>kilogram (kg)</strong>; konsentrasi air dalam <strong>mg/L</strong> kecuali parameter biologi (JPT/100 ml atau CFU/100 ml).</li>
          <li>Tanggal mengikuti ISO-8601 (<code className="text-xs bg-ink-100 px-1 rounded">YYYY-MM-DD</code>). Beberapa tanggal di sheet harian Pengolahan Sampah diperbaiki dari serial Excel terbalik (M/D → D/M) dan ditandai di JSON.</li>
          <li>Tanda <code className="text-xs bg-ink-100 px-1 rounded">^</code> di Laporan Hasil Uji menunjukkan nilai di atas baku mutu. Untuk parameter seperti DO (oksigen terlarut) yang baku mutunya bersifat <em>minimum</em>, status kepatuhan dihitung ulang dengan arah yang benar.</li>
          <li>Hasil di bawah limit deteksi (mis. <code className="text-xs bg-ink-100 px-1 rounded">&lt;0,016</code>) disimpan sebagai nilai limit dengan flag <code className="text-xs bg-ink-100 px-1 rounded">below_detection_limit: true</code>.</li>
          <li>Notasi ilmiah (mis. <code className="text-xs bg-ink-100 px-1 rounded">24 × 10⁷</code>) disimpan sebagai integer dan dipulihkan untuk tampilan.</li>
          <li>Entri yang ditandai "DIPERTANYAKAN" di sumber tidak dihitung dalam rata-rata.</li>
        </ul>
      </section>

      {datasets.map(({ ds, label }) => (
        <DataQualityFlags
          key={ds.dataset_id}
          flags={ds.data_quality_flags}
          title={`Catatan: ${label}`}
        />
      ))}
    </div>
  );
}
