# Spec Data JSON — Dashboard Pemantauan Lingkungan UNPAD

**Versi:** 1.4
**Tanggal:** 2026-07-10
**Status:** Aktif. Versi 1.0 di-freeze 2026-05-14; 1.1–1.4 menyusul, lihat [Changelog](#12-changelog).

Spec ini mengikat kontrak data antara pipeline pembersihan (`.claude/skills/unpad-env-data-cleaner`) dan kedua frontend: HTML statis di `docs/` dan Streamlit di `pages/`. Perubahan struktur JSON harus menaikkan versi minor (1.x → 1.y) dan dicatat di changelog di bagian akhir.

Sumber tunggal nomor versi adalah `SPEC_VERSION` di `scripts/_utils.py`. Ia diterbitkan ke field `version` tiap dataset **dan** ke `data/meta.json`, sehingga tidak bisa lagi bertentangan dengan dokumen ini.

---

## Daftar Isi

1. [Konvensi Umum](#1-konvensi-umum)
2. [Layout Folder Data](#2-layout-folder-data)
3. [Schema: `meta.json`](#3-schema-metajson)
4. [Schema: `shared/locations.json`](#4-schema-sharedlocationsjson)
5. [Schema: `shared/regulations.json`](#5-schema-sharedregulationsjson)
6. [Schema: `pengolahan_sampah.json`](#6-schema-pengolahan_sampahjson)
7. [Schema: `timbulan.json`](#7-schema-timbulanjson)
8. [Schema: `water_quality.json`](#8-schema-water_qualityjson)
9. [Schema: `tree_incidents.json`](#9-schema-tree_incidentsjson)
10. [Schema: `traffic_accidents.json`](#10-schema-traffic_accidentsjson)
11. [Schema: `b3_waste.json`](#11-schema-b3_wastejson)
12. [Aturan Validasi & Rekonsiliasi](#12-aturan-validasi--rekonsiliasi)
13. [Changelog](#13-changelog)

---

## 1. Konvensi Umum

### 1.1 Tipe data primitif

| Aturan | Nilai |
|---|---|
| **Encoding** | UTF-8, tanpa BOM |
| **Indentasi** | 2 spasi |
| **Tanggal** | ISO-8601: `YYYY-MM-DD` (mis. `2026-01-30`) |
| **Bulan** | `YYYY-MM` (mis. `2026-01`) |
| **Waktu** | ISO-8601: `YYYY-MM-DDTHH:mm:ss+07:00` (WIB) |
| **Angka** | Float/integer JavaScript; tanpa pemisah ribuan; desimal `.` (titik) |
| **Null/kosong** | `null` (bukan string kosong) |
| **Boolean** | `true` / `false` |
| **ID** | `kebab-case` ASCII (mis. `outlet-ciparanje`, `tabrak-2roda`) |
| **Label** | Bahasa Indonesia, sesuai sumber asli |

### 1.2 Satuan & nomenklatur

Semua satuan dinyatakan eksplisit di field `unit` atau sebagai suffix nama field (`_kg`, `_mg_per_l`, `_ntu`).

| Domain | Satuan default |
|---|---|
| Massa sampah | `kg` |
| Konsentrasi air | `mg/L` (kecuali biologi: `JPT/100ml` atau `CFU/100ml`) |
| Suhu | `°C` |
| Konduktivitas | `µmhos/cm` |
| Kekeruhan | `NTU` |
| Warna | `TCU` |
| Koordinat | desimal derajat (WGS84), 6 angka di belakang koma |

### 1.3 Field meta yang konsisten di tiap dataset

Setiap file dataset wajib punya:

```json
{
  "dataset_id": "string",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["string"],
  "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "data_quality_flags": [ { "severity": "info|warning|error", "message": "string" } ],
  "data": { ... }
}
```

`severity` flag:
- `info` — observasi netral (mis. periode parsial)
- `warning` — anomali yang perlu disorot di UI (mis. selisih total)
- `error` — data tidak konsisten, jangan dipakai untuk kalkulasi tanpa konfirmasi

### 1.4 Konvensi exceedance untuk parameter berambang batas

Setiap pengukuran dengan baku mutu wajib menyertakan:

```json
{
  "result": 5.2,
  "result_display": "5,2",
  "unit": "mg/L",
  "threshold": {
    "type": "max | min | range | deviation | qualitative",
    "max": 3,
    "min": null,
    "reference": null
  },
  "compliant": false,
  "source_flagged_exceedance": true
}
```

- `compliant` = hasil komputasi terhadap arah baku mutu yang benar (min/max/range).
- `source_flagged_exceedance` = nilai literal tanda `^` di sumber LHU (kadang berbeda dengan `compliant`, mis. DO mestinya `min` 4 mg/L, tapi LHU memberi `^`).
- Untuk parameter di bawah limit deteksi (`<0,016`), simpan sebagai:
  ```json
  { "result": 0.016, "below_detection_limit": true, "result_display": "<0,016" }
  ```

---

## 2. Layout Folder Data

```
data/
├── meta.json                       # metadata dashboard
├── shared/
│   ├── locations.json              # kamus lokasi UNPAD
│   └── regulations.json            # kamus baku mutu
├── pengolahan_sampah.json
├── timbulan.json
├── water_quality.json
├── water_quality_ip.json           # Indeks Pencemaran — TIDAK punya parser
├── tree_incidents.json
├── traffic_accidents.json
├── b3_waste.json
│
├── _ledger/                        # BUKU BESAR — sumber kebenaran, bukan terbitan
└── _baseline.json                  # pengaman anti-regresi, bukan terbitan
```

**Tujuh dataset**, ditambah `meta.json` dan `shared/`.

`_ledger/` dan `_baseline.json` ikut git di `data/` tetapi **tidak diterbitkan** ke `docs/data/`. Menyalin `data/*` secara rekursif akan menaruh buku besar di folder yang disajikan publik.

`water_quality_ip.json` tidak diproduksi parser mana pun dan tidak terdaftar di `PIPELINE`. Ia selamat dari rebuild hanya karena promosi bersifat menyalin, bukan mengganti isi folder.

HTML statis membaca `docs/data/*.json` lewat `fetch()`. Streamlit membaca `data/*.json` langsung dari disk.

---

## 3. Schema: `meta.json`

Metadata global dashboard.

```json
{
  "dashboard": {
    "title": "Dashboard Pemantauan Lingkungan UNPAD",
    "subtitle": "Pusat Pengembangan Kampus Berkelanjutan serta Keselamatan dan Keamanan Lingkungan (PKBKKL)",
    "organization": "Universitas Padjadjaran",
    "owner_email": "k.susanto@geophys.unpad.ac.id",
    "url": "https://dashboard-pk3l.unpad.ac.id",
    "version": "1.0",
    "last_updated": "2026-05-14"
  },
  "datasets": [
    {
      "id": "pengolahan_sampah",
      "label": "Pengolahan Sampah",
      "route": "/sampah/pengolahan",
      "icon": "recycle",
      "period_label": "Des 2025 – Jan 2026",
      "primary_kpi": { "label": "Total Sampah Diolah", "value_field": "total_processed_kg" }
    },
    {
      "id": "timbulan",
      "label": "Timbulan Sampah",
      "route": "/sampah/timbulan",
      "icon": "trash",
      "period_label": "Jan – Apr 2026",
      "primary_kpi": { "label": "Total Timbulan YTD", "value_field": "total_kg" }
    },
    {
      "id": "water_quality",
      "label": "Kualitas Air",
      "route": "/air",
      "icon": "droplet",
      "period_label": "Sep – Okt 2025",
      "primary_kpi": { "label": "Persentase Parameter Patuh", "value_field": "compliance_pct" }
    },
    {
      "id": "tree_incidents",
      "label": "Insiden Vegetasi",
      "route": "/vegetasi",
      "icon": "tree",
      "period_label": "2025",
      "primary_kpi": { "label": "Total Kejadian Pohon", "value_field": "total_events" }
    },
    {
      "id": "traffic_accidents",
      "label": "Kecelakaan Lalu Lintas",
      "route": "/lalu-lintas",
      "icon": "car-crash",
      "period_label": "Apr 2025 – Apr 2026",
      "primary_kpi": { "label": "Total Kecelakaan", "value_field": "total_cases" }
    }
  ],
  "color_palette": {
    "organik": "#16a34a",
    "anorganik": "#2563eb",
    "residu": "#737373",
    "kompos": "#65a30d",
    "rdf": "#0891b2",
    "maggot": "#eab308",
    "dumping": "#ef4444",
    "compliant": "#16a34a",
    "exceedance": "#dc2626",
    "below_detection": "#94a3b8"
  }
}
```

---

## 4. Schema: `shared/locations.json`

Kamus lokasi UNPAD yang direferensikan beberapa dataset.

```json
{
  "version": "1.0",
  "locations": {
    "rsptn": { "label": "RSPTN", "type": "rumah_sakit", "campus": "jatinangor" },
    "fk": { "label": "Fakultas Kedokteran", "type": "fakultas", "campus": "jatinangor" },
    "fkg": { "label": "Fakultas Kedokteran Gigi", "type": "fakultas", "campus": "jatinangor" },
    "fapsi": { "label": "Fakultas Psikologi", "type": "fakultas", "campus": "jatinangor" },
    "fkep": { "label": "Fakultas Keperawatan", "type": "fakultas", "campus": "jatinangor" },
    "fmipa": { "label": "Fakultas MIPA", "type": "fakultas", "campus": "jatinangor" },
    "fapet": { "label": "Fakultas Peternakan", "type": "fakultas", "campus": "jatinangor" },
    "faperta": { "label": "Fakultas Pertanian", "type": "fakultas", "campus": "jatinangor" },
    "ftip": { "label": "Fakultas Teknologi Industri Pertanian", "type": "fakultas", "campus": "jatinangor" },
    "fpik": { "label": "Fakultas Perikanan dan Ilmu Kelautan", "type": "fakultas", "campus": "jatinangor" },
    "ftg": { "label": "Fakultas Teknik Geologi", "type": "fakultas", "campus": "jatinangor" },
    "farmasi": { "label": "Fakultas Farmasi", "type": "fakultas", "campus": "jatinangor" },
    "ppbs": { "label": "Pusat Pelayanan Basic Science (PPBS)", "type": "pusat", "campus": "jatinangor" },
    "bale-santika": { "label": "Bale Santika", "type": "gedung", "campus": "jatinangor" },
    "feb": { "label": "Fakultas Ekonomi dan Bisnis", "type": "fakultas", "campus": "jatinangor" },
    "fikom": { "label": "Fakultas Ilmu Komunikasi", "type": "fakultas", "campus": "jatinangor" },
    "fh": { "label": "Fakultas Hukum", "type": "fakultas", "campus": "jatinangor" },
    "fisip": { "label": "Fakultas Ilmu Sosial dan Ilmu Politik", "type": "fakultas", "campus": "jatinangor" },
    "fib": { "label": "Fakultas Ilmu Budaya", "type": "fakultas", "campus": "jatinangor" },
    "indomaret": { "label": "Indomaret Kampus", "type": "komersial", "campus": "jatinangor" },
    "sc": { "label": "Student Center", "type": "gedung", "campus": "jatinangor" },
    "lapangan-merah": { "label": "Lapangan Merah", "type": "lapangan", "campus": "jatinangor" },
    "gor-jati": { "label": "GOR Jati", "type": "olahraga", "campus": "jatinangor" },
    "mru": { "label": "MRU", "type": "gedung", "campus": "jatinangor" },
    "ciparanje": { "label": "Ciparanje", "type": "area", "campus": "jatinangor" },
    "rektorat": { "label": "Rektorat", "type": "gedung", "campus": "jatinangor" },
    "bale-wilasa": { "label": "Bale Wilasa", "type": "gedung", "campus": "jatinangor" },
    "tugu-makalangan": { "label": "Tugu Makalangan", "type": "landmark", "campus": "jatinangor" },
    "sekebitung": { "label": "Sekebitung", "type": "titik-sampling-air", "lat": -6.909917, "lon": 107.769778 },
    "outlet-ciparanje": { "label": "Outlet Ciparanje", "type": "titik-sampling-air", "lat": -6.911361, "lon": 107.771000 },
    "embung": { "label": "Badan Air Embung", "type": "titik-sampling-air", "lat": -6.916250, "lon": 107.773167 },
    "inlet-ekoriparian": { "label": "Inlet Ekoriparian", "type": "titik-sampling-air", "lat": -6.930806, "lon": 107.773361 },
    "badan-ekoriparian": { "label": "Badan Air Ekoriparian", "type": "titik-sampling-air", "lat": -6.931194, "lon": 107.774167 },
    "outlet-ekoriparian": { "label": "Outlet Ekoriparian", "type": "titik-sampling-air", "lat": -6.931972, "lon": 107.774167 },
    "ipal-kimia": { "label": "Outlet IPAL Prodi Kimia (Klinik)", "type": "titik-sampling-limbah", "lat": -6.931833, "lon": 107.776583 },
    "ipal-rs": { "label": "Outlet IPAL Rumah Sakit UNPAD", "type": "titik-sampling-limbah", "lat": -6.931167, "lon": 107.772639 },
    "sumur-pantau": { "label": "Sumur Pantau", "type": "titik-sampling-tanah", "lat": -6.924861, "lon": 107.774250 }
  }
}
```

---

## 5. Schema: `shared/regulations.json`

Kamus baku mutu yang direferensikan dataset air.

```json
{
  "version": "1.0",
  "regulations": {
    "ppri-22-2021-vi-kelas-2": {
      "full_name": "Peraturan Pemerintah Republik Indonesia Nomor 22 Tahun 2021, Lampiran VI Kelas 2",
      "short_name": "PPRI 22/2021 Kelas 2",
      "scope": "Air baku untuk prasarana/sarana rekreasi air, pembudidayaan ikan air tawar, peternakan, dan pertanaman.",
      "year": 2021
    },
    "permen-lh-5-2014-xliv": {
      "full_name": "Peraturan Menteri Lingkungan Hidup RI No. 5 Tahun 2014, Lampiran XLIV",
      "short_name": "Permen LH 5/2014 XLIV",
      "scope": "Baku mutu air limbah bagi usaha dan/atau kegiatan laboratorium klinik.",
      "year": 2014
    },
    "permen-lh-5-2014-xlvii": {
      "full_name": "Peraturan Menteri Lingkungan Hidup RI No. 5 Tahun 2014, Lampiran XLVII",
      "short_name": "Permen LH 5/2014 XLVII",
      "scope": "Baku mutu air limbah bagi usaha dan/atau kegiatan rumah sakit.",
      "year": 2014,
      "has_class_split": true,
      "classes": ["Gol. I", "Gol. II"]
    },
    "permenkes-2-2023": {
      "full_name": "Peraturan Menteri Kesehatan RI Nomor 2 Tahun 2023",
      "short_name": "Permenkes 2/2023",
      "scope": "Standar baku mutu kesehatan lingkungan dan persyaratan kesehatan air untuk keperluan higiene sanitasi.",
      "year": 2023
    },
    "sk-gub-jabar-6": {
      "full_name": "Surat Keputusan Gubernur Kepala Daerah Tingkat I Jawa Barat Nomor 6",
      "short_name": "SK Gub Jabar 6",
      "scope": "Baku mutu air permukaan tingkat provinsi Jawa Barat (acuan Total Nitrogen)."
    }
  }
}
```

---

## 6. Schema: `pengolahan_sampah.json`

Sumber: `Data Pengolahan Sampah.xlsx` (sheet Overview + Des25 + Jan26).

### 6.1 Struktur

```json
{
  "dataset_id": "pengolahan_sampah",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["Data Pengolahan Sampah.xlsx"],
  "period": { "start": "2025-12-01", "end": "2026-01-31" },
  "unit_default": "kg",
  "data_quality_flags": [
    {
      "severity": "info",
      "message": "Tanggal pada Des25 baris 1-10 dan Jan26 baris 1-5 diperbaiki dari serial Excel terbalik (M/D → D/M)."
    },
    {
      "severity": "warning",
      "message": "Total Anorganik Januari 2026 di sheet Overview (1.233 kg) tidak cocok dengan total kolom Anorganik di sheet rinci (1.693 kg). Selisih 460 kg. Dashboard memakai nilai sheet rinci."
    },
    {
      "severity": "info",
      "message": "Metode pengolahan baru 'Bubur Maggot' muncul mulai Januari 2026 (2 record, total 390 kg)."
    }
  ],
  "categories": [
    { "id": "organik", "label": "Organik", "color_key": "organik" },
    { "id": "anorganik", "label": "Anorganik", "color_key": "anorganik" },
    { "id": "residu", "label": "Residu", "color_key": "residu" }
  ],
  "processing_methods": [
    { "id": "kompos", "label": "Kompos", "for_category": "organik", "color_key": "kompos" },
    { "id": "rdf", "label": "Bahan RDF", "for_category": "anorganik", "color_key": "rdf" },
    { "id": "maggot", "label": "Bubur Maggot", "for_category": "organik", "color_key": "maggot" },
    { "id": "dumping", "label": "Dumping", "for_category": "residu", "color_key": "dumping" }
  ],
  "monthly_summary": [
    {
      "month": "2025-12",
      "label": "Desember 2025",
      "incoming_kg": 15287,
      "processed_kg": 12878,
      "residual_kg": 2409,
      "output": {
        "kompos_kg": 1805.4,
        "rdf_kg": 771.2,
        "maggot_kg": 0
      },
      "output_total_kg": 2576.6,
      "processing_rate_pct": 84.24,
      "incoming_by_category_kg": { "organik": 8825, "anorganik": 3296, "residu": 3166 }
    },
    {
      "month": "2026-01",
      "label": "Januari 2026",
      "incoming_kg": 14776,
      "processed_kg": 11495,
      "residual_kg": 3281,
      "output": {
        "kompos_kg": 1233,
        "rdf_kg": 994,
        "maggot_kg": 390
      },
      "output_total_kg": 2617,
      "processing_rate_pct": 77.79,
      "incoming_by_category_kg": { "organik": 8767, "anorganik": 4564, "residu": 1445 }
    }
  ],
  "daily_entries": [
    {
      "date": "2025-12-01",
      "date_raw_excel": "1/12/2025",
      "date_corrected_from_md": true,
      "items": [
        {
          "category": "organik",
          "incoming_kg": 70,
          "processed_kg": 70,
          "residual_kg": 0,
          "method": "kompos",
          "output_kg": 15,
          "status": "Proses Komposting"
        },
        {
          "category": "anorganik",
          "incoming_kg": 110,
          "processed_kg": 110,
          "residual_kg": 0,
          "method": "rdf",
          "output_kg": 22,
          "status": "Menunggu Pengiriman"
        },
        {
          "category": "residu",
          "incoming_kg": 70,
          "processed_kg": 0,
          "residual_kg": 70,
          "method": "dumping",
          "output_kg": 0,
          "status": "Geser ke Area Dumping"
        }
      ],
      "totals": { "incoming_kg": 250, "processed_kg": 180, "residual_kg": 70 }
    }
  ]
}
```

### 6.2 Field constraint

| Field | Tipe | Constraint |
|---|---|---|
| `monthly_summary[].processing_rate_pct` | number | `processed_kg / incoming_kg × 100`, 2 desimal |
| `daily_entries[].date` | string | Setelah koreksi M/D, harus dalam rentang `period` |
| `daily_entries[].items[].category` | enum | `organik` \| `anorganik` \| `residu` |
| `daily_entries[].items[].method` | enum | id dari `processing_methods` |
| Invariant | — | `incoming_kg = processed_kg + residual_kg` di tiap baris item |

---

## 7. Schema: `timbulan.json`

Sumber: `Total Timbulan Sampah 2026 (Bulanan).xlsx`.

### 7.1 Struktur

```json
{
  "dataset_id": "timbulan",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["Total Timbulan Sampah 2026  (Bulanan).xlsx"],
  "period": { "start": "2026-01-26", "end": "2026-04-30" },
  "unit_default": "kg",
  "data_quality_flags": [
    {
      "severity": "info",
      "message": "Januari 2026 hanya tercatat 6 hari kerja (26-31 Jan). Rata-rata per hari aktif jauh lebih representatif daripada rata-rata per hari kalender."
    },
    {
      "severity": "warning",
      "message": "April 2026 tercatat 27 ditandai 'DIPERTANYAKAN' di sumber, dikecualikan dari kalkulasi rata-rata aktif."
    },
    {
      "severity": "warning",
      "message": "Februari (99.644 kg) dan April (120.544 kg) jauh di atas Maret (43.160 kg). Perlu konfirmasi apakah ini lonjakan riil atau bias pencatatan."
    },
    {
      "severity": "info",
      "message": "Pemisahan kategori Organik vs Anorganik+Residu baru rapi mulai April 2026; bulan sebelumnya hanya total."
    }
  ],
  "vehicle_sources": [
    { "id": "truk-tim-angsa", "label": "Truk UNPAD (Tim Angsa)", "operator": "UNPAD", "tare_kg": null },
    { "id": "truk-ipdn", "label": "Truk IPDN", "operator": "IPDN", "tare_kg": null },
    { "id": "pickup-unpad", "label": "Pick Up UNPAD", "operator": "UNPAD", "tare_kg": 1288 },
    { "id": "viar", "label": "Viar", "operator": "UNPAD", "tare_kg": 263 },
    { "id": "cator-unpad", "label": "Cator UNPAD", "operator": "UNPAD", "tare_kg": null },
    { "id": "mobil-traga", "label": "Mobil Traga", "operator": "UNPAD", "tare_kg": 1720, "note": "Aset yang tidak terpakai" },
    { "id": "sod-rs", "label": "SOD Rumah Sakit", "operator": "RS UNPAD", "tare_kg": null }
  ],
  "container_tare_kg": { "biru": 3870, "hijau": 3380, "putih": 4190 },
  "categories": [
    { "id": "organik", "label": "Organik (Daun + Ranting)", "color_key": "organik" },
    { "id": "anorganik_residu", "label": "Anorganik + Residu", "color_key": "anorganik" },
    { "id": "sod", "label": "SOD (Sampah Olahan/RS)", "color_key": "residu" }
  ],
  "monthly_summary": [
    {
      "month": "2026-01",
      "label": "Januari 2026",
      "total_kg": 15170,
      "organik_kg": 5916.3,
      "anorganik_residu_kg": 9253.7,
      "sod_kg": 0,
      "days_active": 6,
      "days_in_month": 31,
      "avg_kg_per_active_day": 2528.33,
      "avg_kg_per_calendar_day": 489.35,
      "category_breakdown_available": false
    },
    {
      "month": "2026-02",
      "label": "Februari 2026",
      "total_kg": 99644,
      "organik_kg": 38861.16,
      "anorganik_residu_kg": 60782.84,
      "sod_kg": 0,
      "days_active": 14,
      "days_in_month": 28,
      "avg_kg_per_active_day": 7117.43,
      "avg_kg_per_calendar_day": 3558.71,
      "category_breakdown_available": false
    },
    {
      "month": "2026-03",
      "label": "Maret 2026",
      "total_kg": 43160,
      "organik_kg": 16832.4,
      "anorganik_residu_kg": 26327.6,
      "sod_kg": 0,
      "days_active": 10,
      "days_in_month": 31,
      "avg_kg_per_active_day": 4316,
      "avg_kg_per_calendar_day": 1392.26,
      "category_breakdown_available": false
    },
    {
      "month": "2026-04",
      "label": "April 2026",
      "total_kg": 120544,
      "organik_kg": 47012.16,
      "anorganik_residu_kg": 73531.84,
      "sod_kg": 0,
      "days_active": 16,
      "days_in_month": 30,
      "avg_kg_per_active_day": 7534,
      "avg_kg_per_calendar_day": 4018.13,
      "category_breakdown_available": true
    }
  ],
  "daily_entries": [
    {
      "date": "2026-01-26",
      "day_of_week": "Senin",
      "total_kg": 3170,
      "by_vehicle_kg": {
        "truk-tim-angsa": [1690, 1480]
      },
      "by_category_kg": null,
      "note": null,
      "quality_flag": null
    },
    {
      "date": "2026-04-09",
      "day_of_week": "Kamis",
      "total_kg": 6152,
      "by_vehicle_kg": {
        "truk-tim-angsa": [970, 1230, 2980, 790],
        "pickup-unpad": [182]
      },
      "by_category_kg": { "organik": 2382, "anorganik_residu": 3770, "sod": 0 },
      "note": null,
      "quality_flag": null
    },
    {
      "date": "2026-04-27",
      "day_of_week": "Senin",
      "total_kg": 0,
      "by_vehicle_kg": {},
      "by_category_kg": null,
      "note": "DIPERTANYAKAN — dikecualikan dari avg",
      "quality_flag": "excluded_from_average"
    }
  ]
}
```

### 7.2 Invariant

- `total_kg` di setiap `daily_entry` = jumlah seluruh elemen di `by_vehicle_kg.*`
- Jika `by_category_kg != null`, maka `sum(by_category_kg.*) == total_kg`
- `days_active` di `monthly_summary` = count(`daily_entries` di bulan tsb dengan `total_kg > 0` AND `quality_flag != "excluded_from_average"`)

---

## 8. Schema: `water_quality.json`

Sumber: 9 LHU Laboratorium Ekologi CESS UNPAD, sampling 10–12 Sep 2025.

### 8.1 Struktur

```json
{
  "dataset_id": "water_quality",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["Scan Sertifikat Hasil Uji Air Permukaan, Air Limbah, dan Air Tanah PK3L UNPAD Oktober 2025.pdf"],
  "period": { "start": "2025-09-10", "end": "2025-10-08" },
  "issuing_lab": {
    "name": "Laboratorium Ekologi PULIK CESS UNPAD",
    "accreditation": "KAN LP-1491-IDN",
    "address": "Jl. Sekeloa Selatan I Bandung 40132",
    "head": "Dr. Gemilang Lara Utama S., S.Pt., M.I.L"
  },
  "data_quality_flags": [
    {
      "severity": "info",
      "message": "Tanda '^' di sumber LHU diterapkan ke parameter DO meski baku mutu DO bersifat minimum (≥4 mg/L). Field `compliant` di spec ini mengoreksi arah; `source_flagged_exceedance` mempertahankan tanda asli."
    },
    {
      "severity": "warning",
      "message": "Penomoran parameter Biologi pada LHU 7 dan LHU 8 mengandung typo (nomor 13 muncul dua kali). Spec ini menormalkan ulang nomor berurutan."
    }
  ],
  "parameter_dictionary": {
    "suhu": { "label": "Suhu", "unit": "°C", "category": "fisika" },
    "dhl": { "label": "Daya Hantar Listrik (DHL)", "unit": "µmhos/cm", "category": "fisika" },
    "tss": { "label": "Padatan Tersuspensi Total (TSS)", "unit": "mg/L", "category": "fisika" },
    "tds": { "label": "Padatan Terlarut Total (TDS)", "unit": "mg/L", "category": "fisika" },
    "kekeruhan": { "label": "Kekeruhan", "unit": "NTU", "category": "fisika" },
    "warna": { "label": "Warna", "unit": "TCU", "category": "fisika" },
    "bau": { "label": "Bau", "unit": null, "category": "fisika" },
    "ph": { "label": "pH", "unit": null, "category": "kimia" },
    "kesadahan": { "label": "Kesadahan (CaCO₃)", "unit": "mg/L", "category": "kimia" },
    "klorida": { "label": "Klorida", "unit": "mg/L", "category": "kimia" },
    "fe": { "label": "Besi (Fe)", "unit": "mg/L", "category": "kimia" },
    "mn": { "label": "Mangan (Mn)", "unit": "mg/L", "category": "kimia" },
    "ni": { "label": "Nikel (Ni)", "unit": "mg/L", "category": "kimia" },
    "zn": { "label": "Seng (Zn)", "unit": "mg/L", "category": "kimia" },
    "cu": { "label": "Tembaga (Cu)", "unit": "mg/L", "category": "kimia" },
    "cr_total": { "label": "Krom Total (Cr)", "unit": "mg/L", "category": "kimia" },
    "cr6": { "label": "Krom Heksavalen (Cr⁶⁺)", "unit": "mg/L", "category": "kimia" },
    "cd": { "label": "Kadmium (Cd)", "unit": "mg/L", "category": "kimia" },
    "pb": { "label": "Timbal (Pb)", "unit": "mg/L", "category": "kimia" },
    "bod": { "label": "BOD", "unit": "mg/L", "category": "kimia" },
    "cod": { "label": "COD", "unit": "mg/L", "category": "kimia" },
    "do": { "label": "Oksigen Terlarut (DO)", "unit": "mg/L", "category": "kimia", "threshold_direction": "min" },
    "tn": { "label": "Total Nitrogen", "unit": "mg/L", "category": "kimia" },
    "no3_n": { "label": "Nitrat sebagai N (NO₃-N)", "unit": "mg/L", "category": "kimia" },
    "no2_n": { "label": "Nitrit sebagai N (NO₂-N)", "unit": "mg/L", "category": "kimia" },
    "po4": { "label": "Orto Fosfat (PO₄³⁻)", "unit": "mg/L", "category": "kimia" },
    "minyak_lemak": { "label": "Minyak dan Lemak", "unit": "mg/L", "category": "kimia" },
    "mpn_ecoli": { "label": "MPN E. coli", "unit": "JPT/100ml", "category": "biologi" },
    "mpn_coliform": { "label": "MPN Coliform", "unit": "JPT/100ml", "category": "biologi" },
    "ecoli_cfu": { "label": "E. coli", "unit": "CFU/100ml", "category": "mikrobiologi" },
    "coliform_cfu": { "label": "Total Coliform", "unit": "CFU/100ml", "category": "mikrobiologi" }
  },
  "reports": [
    {
      "report_no": "1060810/LHU/AP/2025",
      "order_no": "6910/PJL/LE/IX/2025",
      "sample_code": "2509430 AP S",
      "sample_type": "air_permukaan",
      "location_id": "sekebitung",
      "coordinates_dms": "S 06°54'35,7\" - E 107°46'11,2\"",
      "regulation_id": "ppri-22-2021-vi-kelas-2",
      "sampling_method": "SNI 6989.57-2008",
      "sampling_date": "2025-09-10",
      "received_date": "2025-09-10",
      "testing_period": { "start": "2025-09-10", "end": "2025-10-03" },
      "report_date": "2025-10-08",
      "ambient_temp_c": 25,
      "measurements": [
        {
          "parameter_id": "suhu",
          "result": 26,
          "result_display": "26",
          "below_detection_limit": false,
          "threshold": { "type": "deviation", "max_dev": 3, "reference": "ambient" },
          "compliant": true,
          "source_flagged_exceedance": false,
          "method": "SNI 06-6989.23-2005"
        },
        {
          "parameter_id": "ph",
          "result": 6.67,
          "result_display": "6,67",
          "below_detection_limit": false,
          "threshold": { "type": "range", "min": 6, "max": 9 },
          "compliant": true,
          "source_flagged_exceedance": false,
          "method": "SNI 6989.11:2019"
        },
        {
          "parameter_id": "bod",
          "result": 5.2,
          "result_display": "5,2",
          "below_detection_limit": false,
          "threshold": { "type": "max", "max": 3 },
          "compliant": false,
          "source_flagged_exceedance": true,
          "method": "SNI 6989.72:2009"
        },
        {
          "parameter_id": "do",
          "result": 5.5,
          "result_display": "5,5",
          "below_detection_limit": false,
          "threshold": { "type": "min", "min": 4 },
          "compliant": true,
          "source_flagged_exceedance": true,
          "compliance_note": "DO baku mutu Kelas 2 adalah minimum 4 mg/L; hasil 5,5 mg/L menunjukkan kualitas oksigen baik meski LHU memberi tanda '^'."
        },
        {
          "parameter_id": "tn",
          "result": 36.209,
          "result_display": "36,209",
          "below_detection_limit": false,
          "threshold": { "type": "max", "max": 15 },
          "compliant": false,
          "source_flagged_exceedance": true,
          "method": "SK Gub KDH Tk I Jabar No 6"
        },
        {
          "parameter_id": "mpn_ecoli",
          "result": 240000000,
          "result_display": "24 × 10⁷",
          "below_detection_limit": false,
          "threshold": { "type": "max", "max": 1000 },
          "compliant": false,
          "source_flagged_exceedance": true,
          "method": "APHA 9221 E"
        },
        {
          "parameter_id": "cu",
          "result": 0.016,
          "result_display": "<0,016",
          "below_detection_limit": true,
          "threshold": { "type": "max", "max": 0.02 },
          "compliant": true,
          "source_flagged_exceedance": false,
          "method": "SNI 6989-84:2019"
        }
      ],
      "summary": {
        "total_parameters": 19,
        "compliant_count": 14,
        "non_compliant_count": 5,
        "non_compliant_parameters": ["bod", "tn", "mpn_ecoli", "mpn_coliform"],
        "compliance_pct": 73.68
      }
    }
  ],
  "aggregate_summary": {
    "by_sample_type": {
      "air_permukaan": { "reports": 6, "compliance_pct_avg": 70.0, "common_exceedances": ["bod", "mpn_ecoli", "mpn_coliform"] },
      "air_limbah": { "reports": 2, "compliance_pct_avg": 92.0, "common_exceedances": ["mpn_coliform"] },
      "air_sumur": { "reports": 1, "compliance_pct_avg": 60.0, "common_exceedances": ["kekeruhan", "warna", "cr6", "fe", "ecoli_cfu"] }
    }
  }
}
```

### 8.2 Catatan implementasi water_quality

1. **Multi-class threshold** (LHU 8 RS UNPAD): `threshold` boleh berbentuk array dua entry, `compliant` dievaluasi terhadap **Gol. I** (lebih ketat) sebagai default, sambil menyimpan `compliant_gol_2` opsional.
2. **Tanggal `report_date`** ada di footer setiap LHU; meski sama (8 Okt 2025), tetap disimpan eksplisit untuk audit.
3. `mpn_ecoli` & `mpn_coliform` di-store sebagai integer biasa (mis. `240000000` = `24 × 10⁷`); `result_display` mempertahankan notasi ilmiah asli untuk UI.

---

## 9. Schema: `tree_incidents.json`

Sumber: insiden vegetasi 2025.

```json
{
  "dataset_id": "tree_incidents",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.xlsx"],
  "period": { "start": "2025-01-01", "end": "2025-12-31" },
  "data_quality_flags": [
    {
      "severity": "info",
      "message": "Cell 'Farmasi Oktober' di sumber hanya berisi angka '1' tanpa keterangan jenis kejadian; ditandai 'unspecified'."
    }
  ],
  "event_types": [
    { "id": "penebangan", "label": "Penebangan Pohon", "severity": "planned" },
    { "id": "pemangkasan", "label": "Pemangkasan Pohon", "severity": "planned" },
    { "id": "pohon_roboh", "label": "Pohon Roboh", "severity": "incident" },
    { "id": "pohon_patah", "label": "Pohon Patah", "severity": "incident" },
    { "id": "unspecified", "label": "Tidak diketahui", "severity": "unknown" }
  ],
  "monthly_totals": [
    { "month": "2025-01", "penebangan": 1, "pemangkasan": 3, "pohon_roboh": 2, "pohon_patah": 0, "total": 6 },
    { "month": "2025-02", "penebangan": 1, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 1 },
    { "month": "2025-03", "penebangan": 0, "pemangkasan": 1, "pohon_roboh": 0, "pohon_patah": 0, "total": 1 },
    { "month": "2025-04", "penebangan": 0, "pemangkasan": 1, "pohon_roboh": 0, "pohon_patah": 0, "total": 1 },
    { "month": "2025-05", "penebangan": 0, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 0 },
    { "month": "2025-06", "penebangan": 0, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 0 },
    { "month": "2025-07", "penebangan": 0, "pemangkasan": 1, "pohon_roboh": 4, "pohon_patah": 0, "total": 5 },
    { "month": "2025-08", "penebangan": 1, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 1 },
    { "month": "2025-09", "penebangan": 1, "pemangkasan": 0, "pohon_roboh": 1, "pohon_patah": 0, "total": 2 },
    { "month": "2025-10", "penebangan": 1, "pemangkasan": 1, "pohon_roboh": 0, "pohon_patah": 0, "total": 2 },
    { "month": "2025-11", "penebangan": 0, "pemangkasan": 0, "pohon_roboh": 0, "pohon_patah": 0, "total": 0 },
    { "month": "2025-12", "penebangan": 0, "pemangkasan": 2, "pohon_roboh": 4, "pohon_patah": 7, "total": 13 }
  ],
  "yearly_totals": {
    "penebangan": 5,
    "pemangkasan": 8,
    "pohon_roboh": 11,
    "pohon_patah": 7,
    "unspecified": 1,
    "total": 32
  },
  "incidents_by_location": [
    {
      "location_id": "rsptn",
      "monthly": [
        { "month": "2025-01", "events": [{ "type": "pohon_roboh", "count": 1 }] },
        { "month": "2025-02", "events": [{ "type": "penebangan", "count": 1 }] },
        { "month": "2025-07", "events": [{ "type": "penebangan", "count": 1 }] },
        { "month": "2025-08", "events": [{ "type": "penebangan", "count": 1 }] },
        { "month": "2025-10", "events": [{ "type": "pohon_roboh", "count": 1 }] }
      ],
      "total": 5
    },
    {
      "location_id": "fh",
      "monthly": [
        { "month": "2025-06", "events": [{ "type": "pohon_roboh", "count": 2 }] },
        { "month": "2025-10", "events": [{ "type": "pohon_patah", "count": 1 }] }
      ],
      "total": 3
    },
    {
      "location_id": "ciparanje",
      "monthly": [
        { "month": "2025-06", "events": [{ "type": "pohon_roboh", "count": 2 }] },
        { "month": "2025-07", "events": [{ "type": "pohon_roboh", "count": 1 }] },
        { "month": "2025-10", "events": [{ "type": "pohon_patah", "count": 1 }] }
      ],
      "total": 4
    }
  ]
}
```

---

## 10. Schema: `traffic_accidents.json`

Sumber: kecelakaan lalu lintas kawasan UNPAD 2025–2026.

```json
{
  "dataset_id": "traffic_accidents",
  "version": "1.0",
  "generated_at": "2026-05-14T10:00:00+07:00",
  "source_files": ["Kecelakaan Lalu Lintas.xlsx"],
  "period": { "start": "2025-04-01", "end": "2026-04-30" },
  "data_quality_flags": [
    {
      "severity": "warning",
      "message": "Total Kasus 2025 tercatat 33 di sumber, namun penjumlahan baris jenis hanya menghasilkan ~26. Selisih kemungkinan karena rincian bulanan tidak lengkap. Field `total_yearly` mengikuti angka yang tertulis di sumber, `total_yearly_computed` mengikuti penjumlahan tersedia."
    },
    {
      "severity": "info",
      "message": "Persentase di sumber dihitung terhadap total tahun (mis. 33 untuk 2025); untuk 2026 yang masih parsial, persentase dihitung ulang berdasarkan total YTD."
    }
  ],
  "vehicle_types": [
    { "id": "tunggal_motor", "label": "Tunggal Sepeda Motor" },
    { "id": "tunggal_mobil", "label": "Tunggal Mobil" },
    { "id": "beam", "label": "Beam (sepeda listrik)" },
    { "id": "tabrak_2roda", "label": "Tabrakan antar roda dua" },
    { "id": "tabrak_2roda_beam", "label": "Tabrakan roda dua dan Beam" },
    { "id": "tabrak_2roda_4roda", "label": "Tabrakan roda dua dan roda empat" },
    { "id": "tabrak_4roda_beam", "label": "Tabrakan roda empat dan Beam" },
    { "id": "pejalan_kaki", "label": "Pejalan kaki" }
  ],
  "yearly": [
    {
      "year": 2025,
      "total_yearly_reported": 33,
      "total_yearly_computed": 26,
      "monthly": [
        { "month": "2025-04", "by_type": { "tunggal_mobil": 1 }, "total": 1 },
        { "month": "2025-06", "by_type": { "tunggal_mobil": 1, "tabrak_2roda": 1 }, "total": 2 },
        { "month": "2025-08", "by_type": { "tunggal_motor": 3 }, "total": 3 },
        { "month": "2025-09", "by_type": { "tunggal_motor": 6, "beam": 2, "tabrak_2roda": 3, "tabrak_2roda_beam": 1, "tabrak_2roda_4roda": 2, "pejalan_kaki": 2 }, "total": 16 },
        { "month": "2025-10", "by_type": { "tunggal_motor": 3, "tunggal_mobil": 1, "tabrak_2roda_4roda": 2 }, "total": 6 },
        { "month": "2025-11", "by_type": { "tunggal_motor": 1, "beam": 1, "tabrak_2roda": 1 }, "total": 3 },
        { "month": "2025-12", "by_type": { "tunggal_motor": 2 }, "total": 2 }
      ]
    },
    {
      "year": 2026,
      "total_yearly_reported": 4,
      "total_yearly_computed": 4,
      "ytd_through_month": "2026-04",
      "monthly": [
        { "month": "2026-01", "by_type": { "tunggal_motor": 1, "tunggal_mobil": 1, "tabrak_2roda": 1 }, "total": 3 },
        { "month": "2026-02", "by_type": {}, "total": 0 },
        { "month": "2026-03", "by_type": { "tunggal_motor": 1 }, "total": 1 },
        { "month": "2026-04", "by_type": { "tabrak_4roda_beam": 1 }, "total": 1 }
      ]
    }
  ],
  "incidents_detail_2026": [
    { "no": 1, "month": "2026-01", "type": "tunggal_mobil", "location_id": "faperta", "count": 1, "location_label_raw": "Pertanian" },
    { "no": 2, "month": "2026-01", "type": "tabrak_2roda", "location_id": "tugu-makalangan", "count": 1, "location_label_raw": "Tugu Makalangan" },
    { "no": 3, "month": "2026-01", "type": "tunggal_motor", "location_id": "fkg", "count": 1, "location_label_raw": "FKG" },
    { "no": 4, "month": "2026-01", "type": "tabrak_4roda_beam", "location_id": "feb", "count": 1, "location_label_raw": "FEB", "note": "Beam dan Mobil" }
  ]
}
```

---

## 11. Schema: `b3_waste.json`

Logbook limbah bahan berbahaya dan beracun per lembaga dan kode limbah, mengacu **PP 22/2021 Lampiran IX**. Sumber: `Logbook Limbah B3.xlsx` di `Data dan Pengetahuan/Limbah B3/`.

### 11.1 Struktur

```json
{
  "dataset_id": "b3_waste",
  "version": "1.4",
  "summary": {
    "total_entries": 468,
    "total_volume_liter": 13173.58,
    "total_mass_kg": 6853.96,
    "unique_lembaga": 7,
    "unique_kode_limbah": 21,
    "months_with_data": 15
  },
  "monthly_totals": [ { "month": "2026-06", "label": "Juni 2026", "entries": 60, "volume_liter": 0, "mass_kg": 0, "by_kategori": {} } ],
  "by_lembaga":     [ { "lembaga": "Fakultas Farmasi", "entries": 0, "volume_liter": 0, "mass_kg": 0 } ],
  "by_kode_limbah": [ { "kode": "A106d", "entries": 176, "volume_liter": 0, "mass_kg": 0, "kategori": ["Cair"] } ],
  "entries": [
    {
      "month": "2026-06", "date": "2026-06-04",
      "lembaga": "Fakultas Teknik Industri Pertanian",
      "limbah": "Limbah Kalium dikromat",
      "volume": 200, "satuan": "Mili Liter",
      "volume_liter": 0.2, "mass_kg": 0.0,
      "kode_limbah": "A338-1", "kode_sumber": "kamus", "kode_status": "disahkan",
      "kategori": "Cair"
    }
  ],
  "tps_logbook": {
    "summary": { "entri_masuk": 108, "entri_keluar": 28, "pengiriman": 2,
                 "total_masuk_kg": 13497.863, "total_keluar_kg": 13496.863,
                 "sisa_di_tps_kg": 1 },
    "pengiriman":    [ { "tanggal_keluar": "2026-03-02", "tujuan": "PT DAME ALAM SEJAHTERA",
                         "periode_masuk": { "start": "2025-08-27", "end": "2026-06-12" },
                         "total_masuk_kg": 7542.353, "total_keluar_kg": 7541.353,
                         "selisih_kg": 1, "selisih_per_kode": [] } ],
    "sisa_per_kode": [ { "kode_limbah": "A105d", "masuk_kg": 1, "keluar_kg": 0, "sisa_kg": 1 } ],
    "masuk":  [ { "tanggal": "2026-01-04", "kode_limbah": "A105d", "sumber": "Fakultas Farmasi", "mass_kg": 1 } ],
    "keluar": [ { "tanggal": "2026-03-02", "kode_limbah": "A106d", "mass_kg": 2593.1, "tujuan": "PT DAME ALAM SEJAHTERA" } ]
  }
}
```

### 11.2 Satuan

Satuan dinormalkan **satu kali**, di parser. Tiap entri terbit dengan `volume_liter` dan `mass_kg` yang sudah dikonversi; frontend menjumlahkan field itu dan **tidak boleh** menebak dari teks `satuan`.

| Satuan sumber | Menjadi |
|---|---|
| `Liter`, `L` | `volume_liter` × 1 |
| `Mili Liter`, `mL`, `cc` | `volume_liter` × 0,001 |
| `Kg`, `kilogram` | `mass_kg` × 1 |
| `Gram`, `Ton` | `mass_kg` × 0,001 / × 1000 |
| `Buah`, `pcs`, `botol` | cacah — 0 pada keduanya, terbit sebagai flag `warning` |

Satuan di luar tabel itu **menghentikan build** (`return 1`). Bukan diabaikan.

### 11.3 Provenance kode limbah

| Field | Nilai | Arti |
|---|---|---|
| `kode_sumber` | `excel` | Kolom `Kode Limbah` di logbook terisi |
| | `kamus` | Sel kosong; kode diambil dari `data/_ledger/b3_waste_kode.csv` |
| | `kosong` | Tidak ada kode di mana pun; masuk keranjang `—` |
| `kode_status` | `tercatat` | Berasal dari Excel |
| | `usulan` | Dari kamus, **belum disahkan** penanggung jawab B3 |
| | `disahkan` | Dari kamus, sudah disahkan; tanggal dan pengesah tercatat di kamus |

**Excel selalu menang.** Kamus hanya dipakai bila sel Excel kosong. Bila keduanya terisi dan berbeda, kode Excel dipakai dan terbit flag `warning` berisi keduanya.

Notasi kode diselaraskan ke penulisan Lampiran IX: huruf besar, tiga angka, sufiks huruf **kecil** (`A106d`, `B104d`), atau kode industri `A337-1`. Provenance **tidak boleh** dititipkan pada besar-kecil huruf.

### 11.4 Invariant

- `summary.total_volume_liter` = Σ `entries[].volume_liter`
- `summary.total_mass_kg` = Σ `entries[].mass_kg`
- `tps_logbook.summary.sisa_di_tps_kg` = `total_masuk_kg` − `total_keluar_kg`
- `pengiriman[].selisih_kg` ≠ 0 berarti ada limbah yang tercatat masuk tetapi tidak tercatat keluar. Jangan diperbaiki; terbitkan sebagai flag.

Akuntansi `tps_logbook` **terpisah** dari `entries`: logbook TPS mencatat semuanya dalam kilogram, sedangkan `entries` memisahkan liter (cair) dan kilogram (padat). Keduanya tidak boleh dijumlahkan begitu saja.

---

## 12. Aturan Validasi & Rekonsiliasi

Skrip `validate.py` harus menjalankan ini sebelum publish:

### 11.1 Cross-dataset

| Aturan | Aksi jika gagal |
|---|---|
| Setiap `location_id` di dataset apa pun harus ada di `shared/locations.json` | Error, hentikan build |
| Setiap `regulation_id` di water_quality harus ada di `shared/regulations.json` | Error |
| `meta.json.datasets[].id` harus cocok dengan file `data/{id}.json` | Error |

### 11.2 Per-dataset

| Dataset | Aturan |
|---|---|
| pengolahan_sampah | Σ `daily_entries[].items[].incoming_kg` per bulan = `monthly_summary[].incoming_kg` (toleransi ±1 kg untuk rounding); jika tidak, append warning flag dengan selisih konkret |
| timbulan | Σ `daily_entries[].total_kg` per bulan = `monthly_summary[].total_kg`; `days_active` konsisten dengan count `total_kg>0` |
| water_quality | `summary.compliance_pct` = `compliant_count / total_parameters × 100`; `non_compliant_parameters` array hanya berisi parameter dengan `compliant: false` |
| tree_incidents | Σ semua `incidents_by_location[].total` ≈ `yearly_totals.total` (toleransi ±2 untuk record `unspecified`) |
| traffic_accidents | `yearly[].monthly[].total` = Σ `by_type.*` |

### 11.3 Format

| Aturan | Tools |
|---|---|
| JSON valid (parseable) | `json.tool` |
| Schema conformance | `ajv` dengan JSON Schema dari `schemas/*.schema.json` (akan ditulis sebagai resource skill) |
| Tidak ada angka magic (semua angka harus traceable ke sumber) | manual review |
| Tidak ada PII | grep email/NIP di seluruh JSON; HANYA `meta.json.dashboard.owner_email` yang boleh berisi email |

---

## 13. Changelog

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 2026-05-14 | Initial spec — frozen sebelum implementasi |
| 1.1 | 2026-07-10 | `traffic_accidents`: `incidents_detail_2026` → **`incidents_detail`**, dengan field wajib `year` di tiap baris. Tahun tidak lagi menempel di nama field maupun di kode parser. |
| 1.2 | 2026-07-10 | `b3_waste`: tiap entri kini wajib memuat **`volume_liter`** dan **`mass_kg`** hasil konversi satuan. Satuan tak dikenal membuat parser **gagal-keras**. |
| 1.3 | 2026-07-10 | `b3_waste`: tiap entri kini wajib memuat **`kode_sumber`** (`excel`/`kamus`/`kosong`) dan **`kode_status`** (`tercatat`/`usulan`/`disahkan`/`""`). Kode limbah yang belum diisi di Excel diambil dari kamus ber-provenance `data/_ledger/b3_waste_kode.csv`. Excel selalu menang atas kamus. Notasi kode diselaraskan ke penulisan Lampiran IX (sufiks huruf kecil). |
| 1.4 | 2026-07-10 | `b3_waste`: bagian baru **`tps_logbook`** — limbah masuk, limbah keluar ke pengolah berizin, pengiriman per tanggal, dan **sisa di TPS**. Sheet `Logbook (...)` tidak lagi dilewati. |

### Catatan migrasi 1.3 → 1.4

Sheet `Logbook (Sep 24 - Jan 26)` selama ini **dilewati** parser dan hanya ditandai flag `info`.
Padahal di sanalah tercatat limbah B3 yang sudah **keluar** dari TPS ke pengolah berizin. Tanpa
itu, dashboard hanya tahu berapa yang masuk, tidak tahu berapa yang sudah diserahkan dan berapa
yang masih tersimpan.

Sejak 1.4 `b3_waste.json` memuat bagian **`tps_logbook`**:

- `summary` — total masuk, total keluar, jumlah pengiriman, dan **`sisa_di_tps_kg`**.
- `pengiriman[]` — satu entri per tanggal penyerahan: tujuan, bukti dokumen, rentang tanggal
  limbah masuk yang terangkut, total masuk vs total keluar, dan `selisih_per_kode`.
- `sisa_per_kode[]` — kode yang jumlah masuk dan keluarnya tidak sama.
- `masuk[]` dan `keluar[]` — baris mentahnya.

**Akuntansinya terpisah dari `entries`.** Logbook TPS mencatat semuanya dalam kilogram; sheet
`Laporan Limbah` memisahkan liter (cair) dan kilogram (padat). Keduanya tidak boleh dijumlahkan
begitu saja.

**Cara membaca sheetnya.** Dua tabel berdampingan dalam satu grid: kolom 1–6 limbah masuk,
kolom 8–13 limbah keluar, barisnya **tidak sejajar**. Tanggal, tujuan, dan bukti dokumen hanya
ditulis di baris pertama tiap pengiriman, jadi dibawa turun (forward-fill). Batas antar-pengiriman
dikenali dari label baris `"Total Jumlah ..."` / `"Total Limbah yang keluar ..."` — **bukan nomor
baris**, supaya tidak rusak bila pemilik menyisipkan baris.

**Anomali yang diterbitkan sebagai flag, bukan diperbaiki diam-diam:**

- Tanggal keluar pengiriman pertama disimpan sebagai **teks** `'30/06/2025'`, bukan tipe tanggal.
  Parser menerimanya tetapi memberi peringatan.
- Pengiriman 2 Maret 2026: kode `A105d` (merkuri) masuk 1 kg tetapi keluar tercatat 0 kg.
- Pengiriman 2 Maret 2026: empat baris limbah masuk bertanggal 12 Juni 2026 — setelah tanggal
  keluarnya sendiri. Mustahil terangkut; hampir pasti salah ketik bulan di sumber. Parser
  **tidak** mengoreksinya.

### Catatan migrasi 1.2 → 1.3

Kolom **Kode Limbah** di logbook Excel kadang kosong. Excel adalah kotak masuk **baca-saja**
(openpyxl merusak rumus ter-cache bila menyimpan ulang), jadi kode yang belum diisi tidak bisa
dilengkapi di sumber. Sebelumnya entri tanpa kode masuk keranjang `—` begitu saja.

Sejak 1.3, kode limbah yang kosong di Excel dilengkapi dari **kamus ber-provenance** di buku besar:

- `data/_ledger/b3_waste_kode.csv` — memetakan entri → kode. Kunci baris gabungan
  **`(tanggal, lembaga, nama_limbah, volume, satuan)`** — stabil terhadap penyisipan baris Excel,
  dan mencakup `tanggal` agar dua entri identik pada tanggal berbeda (dugaan duplikat 4 vs 8 Juni)
  tidak saling menimpa. Tiap baris membawa `kode`, `status`, `ditetapkan_pada`, `dasar`
  (pasal/tabel PP 22/2021 Lampiran IX atau preseden internal), `keyakinan`, dan `catatan`.
- `data/_ledger/b3_waste_kode_alias.csv` — substitusi kode global untuk kode dari kamus. Membalik
  keputusan industri lab (mis. `A338-1`→`A337-3`) cukup **satu baris CSV**, bukan bedah kode.
- **Excel menang.** Kamus dipakai **hanya bila** sel Kode Limbah di Excel kosong. Bila Excel terisi
  dan berbeda dari kamus, kode Excel dipakai dan terbit flag `warning` berisi keduanya.
- Tiap entri terbit dengan `kode_sumber` dan `kode_status`. Kode `usulan` **belum disahkan** PK3L
  dan tidak boleh dipakai untuk manifest/pelaporan; frontend menandainya, tidak menyamarkannya
  sebagai kode resmi.
- Entri yang tetap tanpa kode setelah kamus dipakai tetap masuk keranjang `—` dan tetap
  memunculkan flag `warning`.

**Notasi kode diselaraskan.** Lampiran IX menulis kode Tabel 1 sebagai huruf besar + tiga angka +
sufiks **huruf kecil** (`A106d`, `B104d`), dan kode industri sebagai `A337-1`. Logbook menulis
sufiksnya huruf besar (`A106D`). Bila keduanya dibiarkan hidup berdampingan, `by_kode_limbah`
memecah `A106D` (151 entri) dari `A106d` (25 entri) — satu kode yang sama tampil sebagai dua kotak
di treemap. Lebih buruk lagi, pemecahan itu tidak konsisten: `A337-1` tetap menyatu karena
sufiksnya angka.

Sejak 1.3 `parse_b3_waste.py` menyelaraskan seluruh kode ke notasi Lampiran IX lewat
`normalkan_kode()`, berlaku sama bagi kode dari Excel maupun dari kamus, dan menerbitkan flag
`info` berisi jumlah kode yang diselaraskan. Kode dengan bentuk di luar pola `Axxxy` / `Bxxxy` /
`Axxx-n` **tidak** diubah dan memunculkan flag `warning`.

Provenance kode **tidak boleh dititipkan pada besar-kecil huruf** — itu tugas `kode_status`.

**Dampak angka.** Tidak ada entri lama yang berubah nilainya, tidak ada bulan yang berkurang.
Pengisian kode dari kamus hanya menyentuh entri yang sel Kode Limbah-nya kosong (per Juli 2026:
61 entri usulan Juni–Juli 2026). Yang berubah hanya *penulisan* kode pada 343 entri
(`A106D` → `A106d`), sehingga `unique_kode_limbah` menjadi **21**, bukan 28.

**Pembacaan mundur.** `docs/limbah-b3.html` hanya membaca `kode_limbah` dan `kode`; field baru
diabaikan bila tak ada. Badge "usulan" muncul hanya bila `kode_status === "usulan"`, jadi JSON lama
(tanpa field itu) tetap terbaca tanpa error.

### Catatan migrasi 1.1 → 1.2

Satuan limbah B3 dulu ditafsirkan dari teks, terpisah-pisah, di **tiga tempat**: parser Python
(`satuan.startswith("liter")`) dan empat blok agregasi di `docs/limbah-b3.html`. Ketiganya memakai
logika yang sama, dan ketiganya salah dengan cara yang sama: `"Mili Liter"` tidak lolos uji
`startswith("liter")` dan bukan `"kg"`, sehingga jatuh ke cabang "abaikan".

Akibatnya **15 entri senilai 2.485 L hilang dari seluruh total** tanpa peringatan — termasuk
300 mL limbah sianida (HCN) dan 200 mL kalium dikromat. Delapan di antaranya sudah ikut terbit
di dashboard sejak Februari 2026.

Sejak 1.2:

- Satuan dinormalkan **satu kali**, di `parse_b3_waste.py`, lewat tabel `SATUAN_KE_LITER`,
  `SATUAN_KE_KG`, dan `SATUAN_CACAH`.
- Tiap entri terbit dengan `volume_liter` dan `mass_kg` yang sudah jadi. Frontend menjumlahkan
  field itu dan **tidak boleh** menebak dari teks `satuan` lagi.
- Satuan di luar ketiga tabel itu menghentikan build (`return 1`) — bukan diabaikan.
- Satuan cacah (`Buah`) tetap terhitung sebagai entri, bernilai 0 pada volume dan massa, dan
  memunculkan `data_quality_flags` bertingkat `warning`, bukan hilang diam-diam.

**Dampak angka.** `total_volume_liter` naik 2,485 L dibanding build 1.1. Kenaikan ini adalah
koreksi, bukan data baru: volume itu selalu ada di logbook, hanya tidak pernah terjumlah.

**Pembacaan mundur.** `docs/limbah-b3.html` memakai `e.volume_liter ?? konversi_dari_satuan(e)`.
JSON lama (tanpa kedua field) tetap terbaca, dan fallback-nya kini sudah mengenal `Mili Liter`,
jadi halaman benar bahkan sebelum rebuild dijalankan.

### Catatan migrasi 1.0 → 1.1

Nama field `incidents_detail_2026` mengunci dataset ke satu tahun. Ketika 2027 tiba, parser
melewati sheet tahun itu **diam-diam, tanpa error**, dan frontend tidak akan pernah
menampilkannya.

Sejak 1.1:

- `parse_traffic_accidents_xlsx.py` menemukan tahun dari **nama sheet** (`^\d{4}$`).
  Menambah 2027 cukup dengan menambah sheet bernama `2027` di workbook.
- Tabel "Berdasarkan Lokasi" dibaca dari sheet tahun mana pun, bukan hanya 2026.
- `period.start` dan `period.end` diturunkan dari bulan aktif paling awal dan paling akhir,
  tidak lagi dari konstanta.

**Pembacaan mundur.** `docs/kecelakaan-lalu-lintas.html`, `pages/5_Kecelakaan_Lalu_Lintas.py`,
dan `validate.py` menerima **kedua** nama field — `incidents_detail` lebih dulu, lalu
`incidents_detail_2026`. Jadi JSON lama tetap terbaca sampai rebuild berikutnya berjalan,
dan tidak ada jendela waktu di mana dashboard rusak.

**Dipensiunkan pada versi ini.** `update_traffic_from_xlsx.py` dan `update_timbulan_from_xlsx.py`
menulis langsung ke `data/` dan `docs/data/`, melewati staging, validasi, dan pengaman
anti-regresi. Keduanya kini menolak jalan tanpa flag `--i-know-this-is-retired`.

---

## Lampiran A — JSON Schema (sketsa)

Schema tiap dataset ada di **`.claude/skills/unpad-env-data-cleaner/schemas/*.schema.json`** (bukan `data/schemas/` seperti tertulis di versi lama dokumen ini).

> **Perhatikan.** Berkas schema itu **belum tersambung ke pipeline**. `_utils.py` mendefinisikan `SCHEMAS_DIR` tetapi tidak ada kode yang memakainya; `validate.py` melakukan pemeriksaan manual per dataset, bukan validasi JSON-Schema. Jadi schema di sini adalah dokumentasi kontrak, bukan penjaga. Jangan mengira ia menahan apa pun.

Contoh untuk water_quality (parsial):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "water_quality.schema.json",
  "type": "object",
  "required": ["dataset_id", "version", "generated_at", "reports"],
  "properties": {
    "dataset_id": { "const": "water_quality" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+$" },
    "reports": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["report_no", "location_id", "regulation_id", "measurements"],
        "properties": {
          "measurements": {
            "type": "array",
            "items": {
              "required": ["parameter_id", "result", "compliant"],
              "properties": {
                "compliant": { "type": "boolean" },
                "threshold": {
                  "oneOf": [
                    { "type": "object", "properties": { "type": { "const": "max" }, "max": { "type": "number" } }, "required": ["type", "max"] },
                    { "type": "object", "properties": { "type": { "const": "min" }, "min": { "type": "number" } }, "required": ["type", "min"] },
                    { "type": "object", "properties": { "type": { "const": "range" }, "min": { "type": "number" }, "max": { "type": "number" } }, "required": ["type", "min", "max"] },
                    { "type": "object", "properties": { "type": { "const": "deviation" }, "max_dev": { "type": "number" }, "reference": { "type": "string" } }, "required": ["type", "max_dev"] }
                  ]
                }
              }
            }
          }
        }
      }
    }
  }
}
```
