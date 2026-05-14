# Dashboard Pemantauan Lingkungan UNPAD

Dashboard berbasis web untuk Pusat Keselamatan, Kesehatan Kerja, dan Lingkungan (**PK3L**) Universitas Padjadjaran. Menampilkan lima domain pemantauan: pengolahan sampah, timbulan harian, kualitas air, insiden vegetasi, dan kecelakaan lalu lintas.

## Arsitektur

```
┌──────────────────────────┐    ┌───────────────────────┐   ┌─────────────────┐
│ 5 file MD / XLSX sumber  │ →  │ Skill                  │ → │ data/*.json     │
│ (Pengolahan, Timbulan,   │    │ unpad-env-data-cleaner │   │ (terverifikasi) │
│  Kualitas Air, dst.)     │    │ (Python, deterministik)│   │                 │
└──────────────────────────┘    └───────────────────────┘   └────────┬────────┘
                                                                     │
                                                                     ▼
                                                            ┌─────────────────┐
                                                            │ Next.js 15      │
                                                            │ App Router +    │
                                                            │ Recharts        │
                                                            │ (web dashboard) │
                                                            └─────────────────┘
```

## Persyaratan

- **Python 3.9+** — untuk skill pembersihan data (sudah berjalan).
- **Node.js 20+ (LTS)** — untuk Next.js. Belum terpasang di lingkungan ini; lihat [Instalasi Node.js](#instalasi-nodejs).

## Quick Start

### 1. (Opsional) Rebuild data dari sumber

Jika file MD/XLSX sumber berubah, jalankan skill pembersihan:

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data
```

Output: `data/*.json` (sudah tersedia di repo, tidak wajib jalan).

### 2. Install dependencies Node

```powershell
npm install
```

### 3. Jalankan dev server

```powershell
npm run dev
```

Buka <http://localhost:3000>.

### 4. Build production

```powershell
npm run build
npm start
```

## Struktur Proyek

```
.
├── app/                            # Next.js App Router
│   ├── layout.tsx                  # Layout global + sidebar
│   ├── page.tsx                    # Ringkasan
│   ├── _components/                # KpiCard, Charts, dll.
│   ├── sampah/
│   │   ├── pengolahan/page.tsx
│   │   └── timbulan/page.tsx
│   ├── air/page.tsx
│   ├── vegetasi/page.tsx
│   ├── lalu-lintas/page.tsx
│   └── tentang/page.tsx
├── lib/
│   ├── types.ts                    # TS types (mirror data-spec.md)
│   ├── data.ts                     # Server-side JSON loader
│   └── format.ts                   # Number/date format helpers
├── data/                           # Output skill — JSON terverifikasi
│   ├── meta.json
│   ├── shared/
│   └── *.json
├── data-spec.md                    # Kontrak schema v1.0 (frozen)
├── .claude/skills/
│   └── unpad-env-data-cleaner/     # Skill pembersihan data
├── *.md                            # Sumber data (5 file)
└── *.xlsx                          # Sumber data original
```

## Halaman Dashboard

| Rute | Konten |
|---|---|
| `/` | Ringkasan KPI seluruh domain + penjelasan singkat tiap data |
| `/sampah/pengolahan` | Komposisi sampah masuk, distribusi hasil olahan, rasio pengolahan bulanan |
| `/sampah/timbulan` | Timbulan harian dari 7 sumber kendaraan, breakdown kategori (April+) |
| `/air` | 9 LHU lengkap dengan status kepatuhan per parameter, peta acuan baku mutu |
| `/vegetasi` | Heatmap lokasi × bulan, klasifikasi terencana vs insiden |
| `/lalu-lintas` | Distribusi bulanan per jenis (2025 & 2026 YTD), detail lokasi |
| `/tentang` | Sumber data, baku mutu, metodologi, semua data quality flag |

## Stack & Library

- **Next.js 15** (App Router) — server components untuk data fetching, no client-side data hydration.
- **TypeScript 5** — strict mode aktif.
- **Tailwind CSS 3** — utility-first styling dengan palette kustom di `tailwind.config.ts`.
- **Recharts 2** — semua chart (stacked bar, grouped bar, line, donut). Heatmap memakai CSS grid kustom (tidak ada paket tambahan).
- **Lucide React** — icon library.

Total dependency runtime: ~6 package. Bundle build estimasi < 250 KB gzip.

## Update Data Workflow

1. Edit MD sumber (atau ganti file XLSX dan regenerate MD).
2. Jalankan `python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data`.
3. Periksa exit code: `0` = clean, `2` = ada warning (review di output `validate`).
4. Commit `data/` ke git.
5. Rebuild Next.js (`npm run build`) atau push ke Vercel/Netlify (auto-deploy).

## Deploy ke Vercel

```powershell
npm install -g vercel
vercel
```

Konfigurasi default Vercel kompatibel dengan Next.js 15 App Router; tidak perlu env var untuk versi ini.

## Instalasi Node.js

Versi LTS terbaru bisa didapat dari <https://nodejs.org/>. Cara lain di Windows:

```powershell
# Via winget
winget install OpenJS.NodeJS.LTS

# Atau via NVM for Windows
nvm install lts
nvm use lts
```

Cek versi:

```powershell
node --version    # diharapkan v20.x atau lebih baru
npm --version
```

## Versi & Kontrak Data

- Data spec: `data-spec.md` v1.0 (frozen).
- Setiap dataset JSON mengikuti envelope wajib (`dataset_id`, `version`, `generated_at`, `source_files`, `period`, `data_quality_flags`).
- Tipe TypeScript di `lib/types.ts` mirror dengan spec.
- Perubahan struktur JSON → naik versi spec → naikkan versi parser di skill → sinkronkan tipe TS.

## Lisensi & Kontak

Data milik PK3L Universitas Padjadjaran. Kontak: <k.susanto@geophys.unpad.ac.id>.
