---
name: unpad-env-data-cleaner
description: Clean and normalize UNPAD environmental monitoring data (waste processing, waste generation, water quality, tree incidents, traffic accidents) from Markdown sources into validated JSON conforming to data-spec.md v1.0. Fixes Excel M/D vs D/M date errors, reconciles Overview-vs-detail totals, normalizes water quality threshold direction (max/min/range/deviation), and emits data_quality_flags. Use when user asks to "clean environmental data", "rebuild dashboard JSON", "regenerate data/", or refers to data-spec.md.
---

# UNPAD Environmental Data Cleaner

Skill ini mengubah lima sumber Markdown menjadi JSON tervalidasi siap-dikonsumsi oleh dashboard. Pipeline sepenuhnya deterministik dan idempotent.

## Kapan Dipakai

Pakai skill ini ketika user:
- meminta "bersihkan data lingkungan UNPAD" / "regenerate data/" / "rebuild JSON dashboard"
- mengubah salah satu MD sumber dan ingin sinkron ulang
- menjalankan validasi sebelum deploy
- referensi ke `data-spec.md` v1.0

## Sumber Data

Lima file MD di root project (`e:\Dashboard Pemantauan Lingkungan\`):

| ID Dataset | Sumber MD |
|---|---|
| `pengolahan_sampah` | `Data Pengolahan Sampah.md` |
| `timbulan` | `Total Timbulan Sampah 2026  (Bulanan).md` (perhatikan dua spasi) |
| `water_quality` | `Scan Sertifikat Hasil Uji Air Permukaan, Air Limbah, dan Air Tanah PK3L UNPAD Oktober 2025.md` |
| `tree_incidents` | `Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.md` |
| `traffic_accidents` | `Kecelakaan Lalu Lintas.md` |

Spec lengkap untuk output ada di `data-spec.md` di root project. Jika berubah, naikkan versi schema sebelum modify parser.

## Output

Pipeline menulis ke `<project_root>/data/`:

```
data/
├── meta.json
├── shared/
│   ├── locations.json
│   └── regulations.json
├── pengolahan_sampah.json
├── timbulan.json
├── water_quality.json
├── tree_incidents.json
└── traffic_accidents.json
```

Selama uji coba, `--out <dir>` mengarahkan output ke folder lain (default: `output/` di dalam folder skill).

## Cara Menjalankan

**Pipeline penuh (rekomendasi):**

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data
```

**Per-dataset (untuk debugging):**

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\parse_pengolahan_sampah.py --out data
python .claude\skills\unpad-env-data-cleaner\scripts\parse_timbulan.py --out data
python .claude\skills\unpad-env-data-cleaner\scripts\parse_water_quality.py --out data
python .claude\skills\unpad-env-data-cleaner\scripts\parse_tree_incidents.py --out data
python .claude\skills\unpad-env-data-cleaner\scripts\parse_traffic_accidents.py --out data
```

**Validasi saja:**

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\validate.py --data data
```

Exit code 0 = lulus; 1 = ada error; 2 = ada warning (dashboard tetap bisa di-build, tapi user perlu diberi tahu).

## Aturan Pembersihan Penting

Ringkasan keputusan yang sudah dibuat di `data-spec.md`. Jangan ubah tanpa naik versi schema.

### Tanggal Excel terbalik (M/D vs D/M)

Sheet `Des25` baris awal (12/01/2025 s/d 12/12/2025) dan `Jan26` (01/06/2026 s/d 01/12/2026) berisi tanggal yang ter-parse Excel sebagai M/D, padahal user input D/M. Aturan koreksi:

- Jika `month <= 12` DAN `day <= 12` DAN tanggal terlihat berurutan menaik per bulan, swap → set `date_corrected_from_md: true`.
- Jika `day > 12`, tidak ada ambiguity, biarkan apa adanya.

Implementasi: `scripts/_utils.py::fix_md_to_dm()`.

### Selisih Total Overview vs Detail

Pengolahan Sampah Jan 2026: Overview tulis Anorganik 1.233 kg, sheet detail jumlah 1.693 kg.

- Output JSON menggunakan **nilai sheet detail** (1.693 kg).
- Tambah `data_quality_flag` severity `warning` yang menyebut selisih konkret.

### Threshold Direction (Kualitas Air)

LHU sumber memberi tanda `^` untuk parameter "di atas baku mutu", tapi tidak konsisten: DO baku mutu `≥ 4 mg/L` (minimum), hasil 5,5 mg/L diberi `^` padahal compliant.

- Spec wajib: `threshold.type` ∈ {`max`, `min`, `range`, `deviation`, `qualitative`}.
- `compliant: boolean` dihitung benar berdasarkan `type`.
- `source_flagged_exceedance: boolean` mempertahankan tanda asli untuk audit.

Mapping parameter → threshold type ada di `resources/parameter_thresholds.json`.

### Tanggal "DIPERTANYAKAN" di Timbulan April

April 27 2026 ditandai `DIPERTANYAKAN` di sumber.
- Disimpan sebagai entry dengan `total_kg: 0`, `quality_flag: "excluded_from_average"`.
- Dikecualikan dari kalkulasi `days_active` dan `avg_kg_per_active_day`.

### MPN/CFU dalam Notasi Ilmiah

Hasil seperti `24 × 10⁷` disimpan sebagai integer (`240000000`) di `result`, dan string asli di `result_display`.

### Below Detection Limit

Hasil `<0,016` disimpan sebagai:
```json
{ "result": 0.016, "below_detection_limit": true, "result_display": "<0,016" }
```

## Layout Skill

```
.claude/skills/unpad-env-data-cleaner/
├── SKILL.md                            (file ini)
├── README.md                           (catatan untuk manusia)
├── scripts/
│   ├── _utils.py                       (date helpers, slug, IO)
│   ├── _md_parser.py                   (parser tabel MD generik)
│   ├── build_shared.py                 (locations + regulations)
│   ├── build_meta.py                   (meta.json)
│   ├── parse_pengolahan_sampah.py
│   ├── parse_timbulan.py
│   ├── parse_water_quality.py
│   ├── parse_tree_incidents.py
│   ├── parse_traffic_accidents.py
│   ├── validate.py                     (schema + invariant check)
│   └── run_all.py                      (orchestrator)
├── schemas/
│   └── *.schema.json                   (Draft 2020-12)
├── resources/
│   ├── locations_master.json           (kamus lokasi UNPAD)
│   ├── regulations_master.json         (kamus baku mutu)
│   └── parameter_thresholds.json       (mapping parameter air → threshold)
└── output/                             (default --out untuk testing)
```

## Alur Internal Tiap Parser

1. `argparse` ambil `--out <dir>` dan `--source <md_path>`.
2. Load MD sumber via `_md_parser.read_md_tables()`.
3. Transform ke struktur spec (dengan dataset-specific logic).
4. Hitung agregat (monthly totals, compliance_pct, dsb).
5. Validasi invariant lokal (mis. `incoming_kg = processed_kg + residual_kg`).
6. Append `data_quality_flags` jika invariant gagal.
7. Tulis JSON ke `<out>/<dataset_id>.json` dengan `indent=2, ensure_ascii=False`.
8. Cetak ringkasan ke stdout (jumlah record, flag count).

## Pengembangan Lanjutan

- **Penambahan dataset baru:** ikuti pola `parse_*.py`, tambah entry di `meta.json.datasets`, tambah schema di `schemas/`, daftarkan di `run_all.py`.
- **Update locations:** edit `resources/locations_master.json` (tunggal source of truth) → jalankan `build_shared.py`.
- **Update baku mutu:** edit `resources/regulations_master.json` + `resources/parameter_thresholds.json`.
- **Bump spec version:** edit `data-spec.md` § Changelog, naikkan `"version"` di setiap parser output, sinkronkan schema di `schemas/`.

## Konstrain Runtime

- Python 3.9+ (stdlib saja; tidak ada `pip install`).
- Validasi schema pakai checker manual di `validate.py` (tidak require `jsonschema` package).
- Path harus mendukung Windows: gunakan `pathlib.Path`, encoding `utf-8`.
- Skrip TIDAK boleh modify file MD sumber.
