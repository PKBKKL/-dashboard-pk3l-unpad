---
name: unpad-env-data-cleaner
description: Clean and normalize UNPAD environmental monitoring data (waste processing, waste generation, water quality, tree incidents, traffic accidents, B3 hazardous waste) from the append-only ledger plus Markdown/Excel sources into validated JSON conforming to data-spec.md v1.4. Enforces staging->validate->promote with an anti-regression guard, hard-fails on unknown units or unmapped columns, and emits data_quality_flags. Use when user asks to "clean environmental data", "rebuild dashboard JSON", "regenerate data/", or refers to data-spec.md.
---

# UNPAD Environmental Data Cleaner

Skill ini membangun **tujuh dataset JSON** untuk dashboard. Pipeline deterministik dan idempotent.

Sebelum apa pun, baca `CLAUDE.md` di root repo: dua jaminan yang tidak boleh dilanggar, dan sepuluh hukum besi yang menegakkannya.

## Kapan Dipakai

Pakai skill ini ketika user:
- meminta "bersihkan data lingkungan UNPAD" / "regenerate data/" / "rebuild JSON dashboard"
- mengubah salah satu sumber dan ingin sinkron ulang
- menjalankan validasi sebelum deploy
- merujuk `data-spec.md`

## Sumber Data

Root project ditemukan lewat `find_project_root()` — **jangan hardcode**. (Dokumen ini pernah menulis `e:\Dashboard Pemantauan Lingkungan\`, path yang sudah tidak ada.)

| ID Dataset | Sumber | Lapis |
|---|---|---|
| `timbulan` | `data/_ledger/timbulan.csv` | buku besar |
| `traffic_accidents` | `data/_ledger/traffic_accidents.csv` | buku besar |
| `pengolahan_sampah` | `Data Pengolahan Sampah.md` | MD di root |
| `water_quality` | `Scan Sertifikat Hasil Uji Air … Oktober 2025.md` | MD di root |
| `tree_incidents` | `Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.md` | MD di root |
| `b3_waste` | `Data dan Pengetahuan/Limbah B3/Logbook Limbah B3.xlsx` + `data/_ledger/b3_waste_kode.csv` | XLSX + kamus |
| `water_quality_ip` | **tidak ada parser** — selamat karena promosi hanya menyalin | — |

Buku besar diisi dari Excel di `Data dan Pengetahuan/` lewat `import_inbox.py`, yang **append-only** dan **dry-run bawaan**. Folder itu **BACA-SAJA** bagi mesin: workbook pemilik menyimpan berat sebagai rumus, dan menyimpannya ulang lewat `openpyxl` membuang nilai ter-cache.

Sumber MD lama untuk `timbulan` dan `traffic_accidents` sudah dipindahkan ke `arsip/`. Isinya **lebih miskin** daripada buku besar (timbulan: 278.518 kg vs 498.818 kg). Lihat `arsip/README.md`.

Kontrak keluaran ada di `data-spec.md` **v1.4**. Mengubah struktur JSON berarti menaikkan `SPEC_VERSION` di `scripts/_utils.py`, mencatat di changelog, lalu menyesuaikan parser **dan** frontend.

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

**Per-dataset (untuk debugging).** Arahkan ke folder sementara, **jangan** ke `data/` — parser
tunggal melewati staging, validasi, dan pengaman anti-regresi.

```powershell
$S = ".claude\skills\unpad-env-data-cleaner\scripts"
python $S\parse_pengolahan_sampah.py        --out .tmp
python $S\parse_timbulan_ledger.py          --out .tmp
python $S\parse_water_quality.py            --out .tmp
python $S\parse_tree_incidents.py           --out .tmp
python $S\parse_traffic_accidents_ledger.py --out .tmp
python $S\parse_b3_waste.py                 --out .tmp
```

> Dokumen ini pernah menyuruh menjalankan `parse_timbulan.py` dan `parse_traffic_accidents.py`
> **ke `data/`**. Keduanya sudah **pensiun** dan menolak jalan tanpa `--i-know-this-is-retired`;
> keluarannya juga lebih miskin daripada buku besar. Pakai varian `_ledger`.

**Periksa frontend** (wajib bila `docs/*.html` disentuh):

```powershell
python $S\check_frontend.py
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
│   │   ── pustaka ──
│   ├── _utils.py                       (SPEC_VERSION, date helpers, IO, find_source)
│   ├── _md_parser.py                   (parser tabel MD generik)
│   ├── _ledger.py                      (buku besar: baca/tulis CSV, peta kolom, penguncian)
│   │
│   │   ── orkestrasi ──
│   ├── run_all.py                      (staging -> validate -> promote)
│   ├── validate.py                     (invariant + pengaman anti-regresi)
│   ├── check_frontend.py               (parse docs/*.html dengan tree-sitter)
│   ├── publish_docs.py                 (data/ -> docs/data/, menolak berkas _*)
│   │
│   │   ── kotak masuk -> buku besar ──
│   ├── import_inbox.py                 (Excel -> _ledger, append-only, dry-run bawaan)
│   ├── seed_ledger.py                  (sekali pakai: JSON -> _ledger)
│   │
│   │   ── parser AKTIF (terdaftar di PIPELINE run_all.py) ──
│   ├── build_shared.py                 (locations + regulations)
│   ├── build_meta.py                   (meta.json)
│   ├── parse_pengolahan_sampah.py
│   ├── parse_timbulan_ledger.py
│   ├── parse_water_quality.py
│   ├── parse_tree_incidents.py
│   ├── parse_traffic_accidents_ledger.py
│   ├── parse_b3_waste.py               (+ kamus kode, + logbook TPS)
│   │
│   │   ── PENSIUN: menolak jalan tanpa --i-know-this-is-retired ──
│   ├── parse_timbulan.py               (baca arsip/*.md)
│   ├── parse_timbulan_master.py
│   ├── parse_traffic_accidents.py      (baca arsip/*.md)
│   ├── parse_traffic_accidents_xlsx.py (!! masih dipakai import_inbox.py sebagai PUSTAKA)
│   ├── update_timbulan_from_xlsx.py
│   └── update_traffic_from_xlsx.py
├── schemas/
│   └── *.schema.json                   (dokumentasi kontrak; BELUM dipakai validate.py)
├── resources/
│   ├── locations_master.json           (kamus lokasi UNPAD)
│   ├── regulations_master.json         (kamus baku mutu)
│   └── parameter_thresholds.json       (mapping parameter air -> threshold)
└── output/                             (default --out untuk testing, di-gitignore)
```

**Jangan menghapus `parse_traffic_accidents_xlsx.py`** meski berlabel pensiun. `import_inbox.py`
mengimpornya sebagai pustaka (`LOCATION_ID_MAP`, `MONTHS_ID`, `TYPE_MAP`, `_match_type_id`,
`parse_year_sheet`). Guard pensiunnya hanya di `main()`, jadi impor tetap jalan — tetapi
menghapus berkasnya akan mematikan jalur kotak-masuk kecelakaan yang aktif.

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
