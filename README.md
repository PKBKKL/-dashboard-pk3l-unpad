# Dashboard Pemantauan Lingkungan UNPAD

Dashboard berbasis web untuk Pusat Pengembangan Kampus Berkelanjutan serta Keselamatan dan Keamanan Lingkungan (**PKBKKL**) Universitas Padjadjaran. Menampilkan **tujuh domain** pemantauan: pengolahan sampah, timbulan harian, kualitas air, insiden vegetasi, kecelakaan lalu lintas, limbah B3, dan konsumsi listrik.

**Live:** <https://pkbkkl.github.io/-dashboard-pk3l-unpad/>

> Sebelum menyentuh apa pun di repo ini, baca **[`CLAUDE.md`](CLAUDE.md)**. Di sana ada dua jaminan yang tidak boleh dilanggar dan sepuluh hukum besi yang menegakkannya. Dashboard ini dipakai sebagai rekam jejak resmi, dan sebagian datanya — kode limbah B3 — punya konsekuensi hukum.

## Dua Mode yang Berjalan Paralel

| Mode | Untuk siapa | URL produksi |
|---|---|---|
| **HTML statis** | Publik/embed — load cepat, bisa di-iframe ke website UNPAD | <https://pkbkkl.github.io/-dashboard-pk3l-unpad/> |
| **Streamlit** | Internal/operasional — iterasi cepat, filter interaktif penuh | <https://share.streamlit.io/> (sesuai konfigurasi akun) |

Keduanya membaca **JSON yang sama**. HTML statis membaca `docs/data/`, Streamlit membaca `data/`.

> **Streamlit tertinggal satu domain.** `pages/` belum punya halaman Limbah B3, sedangkan HTML statis punya. Ini kesenjangan yang diketahui, bukan kelalaian yang tak disadari.

## Arsitektur — tiga lapis

```
Kotak masuk    Data dan Pengetahuan\*.xlsx        milik pemilik, BACA-SAJA bagi mesin
      |
      |   import_inbox.py   append-only, dry-run bawaan
      v
Buku besar     data\_ledger\*.csv                 sumber kebenaran, ikut git
      |
      |   parser   staging -> validate -> promote
      v
Terbitan       data\*.json  ->  docs\data\*.json  boleh dibangun ulang kapan saja
      |
      +--> Streamlit (streamlit_app.py + pages\)
      +--> HTML statis (docs\, GitHub Pages)
```

Buku besar baru dipakai **timbulan** dan **traffic_accidents**. Empat dataset lain (`pengolahan_sampah`, `water_quality`, `tree_incidents`, `b3_waste`) masih dibaca langsung dari MD/XLSX oleh parser masing-masing.

`b3_waste` punya **kamus kode ber-provenance** di `data/_ledger/b3_waste_kode.csv`. Kamus hanya dipakai bila sel `Kode Limbah` di Excel kosong; Excel selalu menang.

`water_quality_ip.json` **tidak punya parser** dan tidak terdaftar di `PIPELINE`. Ia selamat dari rebuild karena promosi hanya menyalin, tidak pernah menghapus. Jangan menulis parser untuknya tanpa memastikan tahun 2024 dan 2025 tetap ada di keluarannya.

## Persyaratan

- **Python 3.9+** — untuk pipeline dan Streamlit
- **Git** — untuk sinkronisasi ke GitHub
- **tree-sitter** — hanya bila menyentuh `docs/*.html`:
  `python -m pip install tree-sitter tree-sitter-javascript`

> Versi HTML statis **tidak butuh apa-apa** untuk berjalan — cukup browser modern. `node` tidak dibutuhkan, dan memang tidak terpasang di mesin pemilik.

## Quick Start

### 1. Rebuild data dari sumber

```powershell
$S = ".claude\skills\unpad-env-data-cleaner\scripts"
python $S\run_all.py --out data
```

`run_all.py` menulis ke folder sementara, memvalidasi hasil gabungannya, dan baru mempromosikan ke `data/` bila lolos. Exit code: `0` lulus · `1` error (termasuk regresi data) · `2` warning.

### 2. Terbitkan ke HTML statis

```powershell
python $S\publish_docs.py
```

> Jangan menyalinnya dengan tangan. `Copy-Item data\* docs\data\ -Recurse` akan menerbitkan seluruh buku besar `_ledger/` ke folder publik, dan bahkan `Copy-Item data\*.json docs\data\` ikut membawa `_baseline.json` — namanya memang berakhiran `.json`. `publish_docs.py` menolak setiap berkas berawalan garis bawah, lalu memverifikasi bahwa `docs/data/` benar-benar cocok dengan `data/`.
>
> `python $S\publish_docs.py --periksa` memeriksa tanpa menyalin.

### 3. Periksa frontend (wajib bila `docs/*.html` disentuh)

```powershell
python $S\check_frontend.py
```

`SyntaxError` pada `<script type="module">` mengosongkan **seluruh** halaman, bukan sebagiannya. Ini pernah terjadi: satu kurung tutup liar menerbitkan halaman Limbah B3 dalam keadaan kosong total.

### 4. Jalankan Streamlit

```powershell
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Buka <http://localhost:8501>.

### 5. Jalankan HTML statis secara lokal

```powershell
python -m http.server 8000 --directory docs
```

Butuh HTTP server (bukan `file://`) karena halaman memakai `fetch()` untuk memuat JSON.

## Struktur Proyek

```
.
├── CLAUDE.md                                 # Aturan wajib — baca duluan
├── README.md
├── data-spec.md                              # Kontrak schema v1.4
├── requirements.txt
├── streamlit_app.py                          # Streamlit: home
├── app_helpers.py                            # Streamlit: data loader + format
├── pages/                                    # Streamlit: 5 halaman (belum ada Limbah B3)
├── .streamlit/config.toml
│
├── docs/                                     # HTML statis — akar GitHub Pages
│   ├── index.html                            #   Ringkasan
│   ├── pengolahan-sampah.html
│   ├── timbulan-sampah.html
│   ├── kualitas-air.html
│   ├── insiden-vegetasi.html
│   ├── kecelakaan-lalu-lintas.html
│   ├── limbah-b3.html
│   ├── listrik.html
│   ├── assets/                               #   style.css, common.js, charts.js
│   ├── data/                                 #   salinan JSON untuk fetch()
│   └── .nojekyll                             #   sajikan apa adanya, tanpa Jekyll
│
├── data/                                     # JSON kanonik + buku besar
│   ├── meta.json  shared/  *.json            #   terbitan (disalin ke docs/data/)
│   ├── _ledger/                              #   BUKU BESAR — sumber kebenaran
│   └── _baseline.json                        #   pengaman anti-regresi
│
├── arsip/                                    # sumber MD yang sudah digantikan buku besar
├── nextjs-scaffold/                          # arsip eksperimen React — bukan produksi
│
└── .claude/
    ├── agents/                               # 11 agent pk3l-*
    └── skills/unpad-env-data-cleaner/        # pipeline: scripts/, schemas/, resources/
```

Berkas MD sumber yang **masih aktif** ada di root: `Data Pengolahan Sampah.md`, `Scan Sertifikat … Oktober 2025.md`, dan `Kecelakaan dan Kejadian Kantor Lingkungan Tahun 2025.md`. Sumber XLSX/PDF di-gitignore dan tinggal di `Data dan Pengetahuan/` milik pemilik.

## Halaman Dashboard

| Rute Streamlit | Rute HTML | Konten |
|---|---|---|
| `/` | `/index.html` | Ringkasan KPI lintas domain |
| `/Pengolahan_Sampah` | `/pengolahan-sampah.html` | Komposisi sampah masuk, distribusi hasil olahan, rasio bulanan |
| `/Timbulan_Sampah` | `/timbulan-sampah.html` | Timbulan harian, 4 kategori, 7 sumber kendaraan |
| `/Kualitas_Air` | `/kualitas-air.html` | 9 LHU, status kepatuhan, Indeks Pencemaran, peta titik sampling |
| `/Insiden_Vegetasi` | `/insiden-vegetasi.html` | Heatmap lokasi × bulan, top lokasi |
| `/Kecelakaan_Lalu_Lintas` | `/kecelakaan-lalu-lintas.html` | Distribusi bulanan per tahun, detail per lokasi |
| *(belum ada)* | `/limbah-b3.html` | Timbulan B3 per fakultas dan kode PP 22/2021, penyerahan ke pengolah berizin, sisa di TPS |
| *(belum ada)* | `/listrik.html` | Konsumsi listrik Jatinangor per bulan (batang per tahun) + rata-rata bergerak 12 bulan |

## Stack & Library

**Streamlit:** Streamlit 1.57 · Plotly 6.7 · Pandas 2.3

**HTML statis** (tanpa build, semua via CDN): Tailwind CSS Play CDN · Plotly.js 2.35.2 · Leaflet 1.9.4 · vanilla ES modules, tanpa framework.

**Pipeline:** Python murni. `openpyxl` untuk XLSX, `pypdf` untuk PDF, `tree-sitter` untuk memeriksa frontend.

## Alur Update Data

Jangan melompati langkah. Rinciannya di [`CLAUDE.md`](CLAUDE.md).

```powershell
$S = ".claude\skills\unpad-env-data-cleaner\scripts"

python $S\import_inbox.py                      # dry-run; tidak menulis apa pun
# tunjukkan laporannya ke pemilik, tunggu persetujuan
python $S\import_inbox.py --terapkan           # menambah ke buku besar

python $S\run_all.py --out data                # staging -> validate -> promote
python $S\check_frontend.py                    # bila docs\*.html disentuh

# hanya setelah data baru terbukti benar:
python $S\validate.py --data data --update-baseline

python $S\publish_docs.py                      # data\ -> docs\data\

git add -A ; git commit -m "data: update <bulan/tahun>" ; git push
```

**Jangan pernah** memakai `--skip-validate`, `--allow-regression`, atau `--i-know-this-is-retired` atas inisiatif sendiri.

## Deploy

**GitHub Pages** (HTML statis) — `Settings` → `Pages` → `Deploy from a branch` → branch `main`, folder `/docs`. Rebuild ~1 menit setelah `git push`.

**Streamlit Cloud** — sudah aktif; rebuild otomatis setelah push.

Repo: <https://github.com/PKBKKL/-dashboard-pk3l-unpad> (perhatikan kapitalisasi `PKBKKL`).

## Versi & Kontrak Data

- Data spec: [`data-spec.md`](data-spec.md) **v1.4**. Versinya tunggal, ditetapkan `SPEC_VERSION` di `scripts/_utils.py` dan diterbitkan ke tiap JSON.
- Setiap dataset mengikuti envelope wajib: `dataset_id`, `version`, `generated_at`, `source_files`, `period`, `data_quality_flags`.
- Perubahan struktur JSON → naikkan `SPEC_VERSION`, catat di changelog `data-spec.md`, sesuaikan parser dan frontend.
- Berkas `schemas/*.schema.json` adalah **dokumentasi kontrak**, belum tersambung ke `validate.py`. Validasi saat ini berupa pemeriksaan manual per dataset plus pengaman anti-regresi.

## Lisensi & Kontak

Data milik PKBKKL Universitas Padjadjaran. Kontak: <k.susanto@geophys.unpad.ac.id>.
