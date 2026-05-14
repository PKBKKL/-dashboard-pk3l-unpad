# Dashboard Pemantauan Lingkungan UNPAD

Dashboard berbasis web untuk Pusat Keselamatan, Kesehatan Kerja, dan Lingkungan (**PK3L**) Universitas Padjadjaran. Menampilkan lima domain pemantauan: pengolahan sampah, timbulan harian, kualitas air, insiden vegetasi, dan kecelakaan lalu lintas.

## Dua Mode yang Berjalan Paralel

| Mode | Untuk siapa | URL produksi |
|---|---|---|
| **Streamlit** | Internal/operasional — iterasi cepat, filter interaktif penuh | <https://share.streamlit.io/> (sesuai konfigurasi akun) |
| **HTML statis** | Publik/embed — load cepat, bisa di-iframe ke website UNPAD | GitHub Pages: `https://pkbkkl.github.io/-dashboard-pk3l-unpad/` |

Keduanya membaca **data yang sama** dari skill `unpad-env-data-cleaner`. Jika data diubah, kedua mode otomatis sinkron setelah `git push`.

## Arsitektur

```
┌──────────────────────────┐    ┌──────────────────────────┐   ┌─────────────────┐
│ 5 file MD/XLSX sumber    │ →  │ Skill                    │ → │ data/*.json     │
│ (Pengolahan, Timbulan,   │    │ unpad-env-data-cleaner   │   │ docs/data/*.json│
│  Kualitas Air, dst.)     │    │ (Python, deterministik)  │   │ (terverifikasi) │
└──────────────────────────┘    └──────────────────────────┘   └────────┬────────┘
                                                                        │
                                              ┌─────────────────────────┴───────────────────────┐
                                              ▼                                                 ▼
                                  ┌──────────────────────┐                       ┌────────────────────────┐
                                  │ Streamlit (Python)   │                       │ HTML statis            │
                                  │ streamlit_app.py     │                       │ docs/*.html            │
                                  │ + pages/             │                       │ + Plotly.js + Leaflet  │
                                  │ Deploy: Streamlit    │                       │ Deploy: GitHub Pages   │
                                  │ Cloud                │                       │                        │
                                  └──────────────────────┘                       └────────────────────────┘
```

## Persyaratan

- **Python 3.9+** — untuk skill data cleaner dan Streamlit
- **Git** — untuk sinkronisasi ke GitHub (sudah terpasang)

> Versi HTML statis **tidak butuh apa-apa** untuk berjalan — cukup buka di browser dari GitHub Pages, atau lokal via `python -m http.server`. Yang dibutuhkan hanya browser modern.

## Quick Start

### 1. Rebuild data dari sumber (saat sumber berubah)

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data
Copy-Item -Path "data\*" -Destination "docs\data\" -Recurse -Force
```

Skill menulis ke `data/`; copy ke `docs/data/` agar HTML statis ikut sinkron.

### 2. Jalankan Streamlit (untuk internal/operasional)

```powershell
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Buka <http://localhost:8501>.

### 3. Jalankan HTML statis (untuk preview publik)

```powershell
python -m http.server 8000 --directory docs
```

Buka <http://127.0.0.1:8000>.

> HTML statis butuh HTTP server (bukan `file://`) karena pakai `fetch()` untuk load JSON. `http.server` Python sudah cukup.

## Struktur Proyek

```
.
├── README.md
├── data-spec.md                              # Kontrak schema v1.0
├── requirements.txt                          # streamlit + plotly + pandas
├── streamlit_app.py                          # Streamlit: home
├── pages/                                    # Streamlit: halaman per-domain
├── app_helpers.py                            # Streamlit: data loaders + format
├── .streamlit/config.toml                    # Tema Streamlit
├── docs/                                     # HTML statis (GitHub Pages root)
│   ├── index.html                            #   Ringkasan
│   ├── pengolahan-sampah.html
│   ├── timbulan-sampah.html
│   ├── kualitas-air.html
│   ├── insiden-vegetasi.html
│   ├── kecelakaan-lalu-lintas.html
│   ├── tentang.html
│   ├── assets/
│   │   ├── style.css
│   │   ├── common.js                         #   Data loader, format, sidebar
│   │   └── charts.js                         #   Plotly wrappers
│   ├── data/                                 #   JSON copy untuk fetch()
│   └── .nojekyll                             #   GitHub Pages: serve as-is
├── data/                                     # JSON canonical (terverifikasi)
│   ├── meta.json
│   ├── shared/
│   └── *.json
├── .claude/skills/unpad-env-data-cleaner/    # Pipeline cleaning
└── *.md                                      # 5 file MD sumber (XLSX/PDF di local saja)
```

## Halaman Dashboard

Sama untuk Streamlit dan HTML:

| Rute Streamlit | Rute HTML | Konten |
|---|---|---|
| `/` | `/index.html` | Ringkasan KPI lintas domain + penjelasan singkat |
| `/Pengolahan_Sampah` | `/pengolahan-sampah.html` | Komposisi sampah masuk, distribusi hasil olahan, rasio bulanan |
| `/Timbulan_Sampah` | `/timbulan-sampah.html` | Timbulan harian, breakdown kategori (April+), sumber kendaraan |
| `/Kualitas_Air` | `/kualitas-air.html` | 9 LHU, status kepatuhan, peta titik sampling |
| `/Insiden_Vegetasi` | `/insiden-vegetasi.html` | Heatmap lokasi × bulan, top lokasi |
| `/Kecelakaan_Lalu_Lintas` | `/kecelakaan-lalu-lintas.html` | Distribusi bulanan 2025 & 2026, detail per lokasi |
| `/Tentang_Data` | `/tentang.html` | Sumber, baku mutu, metodologi, data quality flags |

## Stack & Library

**Streamlit:** Streamlit 1.57 · Plotly 6.7 · Pandas 2.3

**HTML statis (zero build, semua via CDN):**
- Tailwind CSS via Play CDN
- Plotly.js 2.35.2
- Leaflet 1.9.4 (untuk peta titik sampling air)
- Tidak ada framework JS — vanilla ES modules

## Update Data Workflow

1. Edit file MD sumber (atau ganti XLSX + regenerate MD).
2. Jalankan skill:
   ```powershell
   python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data
   Copy-Item -Path "data\*" -Destination "docs\data\" -Recurse -Force
   ```
3. Verifikasi exit code: `0` clean, `2` ada warning.
4. Commit:
   ```powershell
   git add data/ docs/data/
   git commit -m "data: update <bulan/tahun>"
   git push
   ```
5. Auto-deploy:
   - **Streamlit Cloud** rebuild dalam ~1 menit
   - **GitHub Pages** rebuild dalam ~1 menit

Kedua mode dashboard akan sinkron otomatis tanpa kerja manual lanjutan.

## Deploy ke GitHub Pages (HTML statis)

1. Push ke repo (sudah dilakukan).
2. Di GitHub: `Settings` → `Pages` → `Source: Deploy from a branch` → pilih branch `main` dan folder `/docs` → Save.
3. Tunggu ~1 menit. URL publik: `https://pkbkkl.github.io/-dashboard-pk3l-unpad/`.

`docs/.nojekyll` memastikan GitHub Pages menyajikan file apa adanya tanpa preprocess Jekyll.

## Deploy ke Streamlit Cloud

Sudah aktif. Untuk re-deploy / manage: <https://share.streamlit.io/>

## Versi & Kontrak Data

- Data spec: `data-spec.md` v1.0 (frozen).
- Setiap dataset JSON mengikuti envelope wajib (`dataset_id`, `version`, `generated_at`, `source_files`, `period`, `data_quality_flags`).
- Perubahan struktur JSON → naik versi spec → naikkan versi parser di skill.

## Lisensi & Kontak

Data milik PK3L Universitas Padjadjaran. Kontak: <k.susanto@geophys.unpad.ac.id>.
