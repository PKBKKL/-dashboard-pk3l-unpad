# Buku Besar — Sumber Kebenaran Dashboard PK3L

> **Baris yang masuk ke sini tidak pernah keluar.**

Folder ini adalah sumber resmi data **timbulan sampah** dan **kecelakaan lalu lintas**.
Dashboard dibangun ulang dari sini, bukan dari Excel.

Berformat teks (CSV) supaya ikut git. `.gitignore` mengecualikan `*.xlsx`, sehingga
workbook Excel **tidak pernah punya riwayat versi**. Buku besar punya. Setiap
perubahan tercatat di `git log` selamanya.

## Aturan emas

**Kotak masuk hanya boleh menambah. Ia tidak pernah bisa mengurangi.**

| Situasi | Tindakan |
|---|---|
| Kunci baru | **TAMBAH** |
| Kunci ada, nilai sama | lewati |
| Kunci ada, nilai berbeda | **TOLAK**, catat konflik. Buku besar menang. |
| Ada di buku besar, hilang dari Excel | lewati — tetap disimpan |
| Kunci di periode terkunci | **TOLAK**, walau nilainya baru |
| Kolom berangka belum dipetakan | **GAGAL KERAS**, impor berhenti |
| Sel rumus tanpa nilai tersimpan | **GAGAL KERAS**, impor berhenti |

## Isi

| Berkas | Isi | Kunci baris |
|---|---|---|
| `timbulan.csv` | fakta harian | `tanggal` |
| `traffic_accidents.csv` | fakta bulanan per jenis | `tahun` + `bulan` + `jenis` |
| `traffic_accidents_detail.csv` | kasus per lokasi | `tahun` + `no` |
| `*.md` | cermin bacaan, **dihasilkan otomatis** | — |
| `b3_waste_kode.csv` | kamus kode limbah B3 (usulan), dipakai bila sel Kode Limbah Excel kosong | `tanggal`+`lembaga`+`nama_limbah`+`volume`+`satuan` |
| `b3_waste_kode_alias.csv` | substitusi kode kamus (mis. flip industri 38→37), satu baris per alias | `dari` |
| `_peta_kolom.csv` | pola header Excel → kategori, berlaku-sejak-tanggal | — |
| `_terkunci.csv` | periode yang tidak boleh diubah | — |
| `_konflik/` | laporan tiap impor yang menolak sesuatu | — |

**Kamus kode limbah B3.** Berbeda dari timbulan/kecelakaan, *fakta* limbah B3 tetap berasal dari
Excel (`Logbook Limbah B3.xlsx`); hanya **kode limbah** yang dilengkapi dari buku besar ini, dan
hanya untuk baris yang sel Kode Limbah-nya kosong di Excel. Excel selalu menang. Seluruh kode di
`b3_waste_kode.csv` berstatus `usulan` sampai disahkan penanggung jawab limbah B3 UNPAD — jangan
ubah `status` menjadi `disahkan` tanpa persetujuan tertulis. Kolom `dasar` merujuk PP 22/2021
Lampiran IX. Kode `usulan` tidak boleh dipakai untuk manifest atau pelaporan.

Nilai turunan **tidak disimpan**: `unpad_kg` = jumlah empat kategori, `total_kg` =
`unpad_kg + ipdn_kg`. Parser menghitungnya, sehingga tidak mungkin bertentangan.

## Cara memakai

```powershell
# 1. Ketik data bulan baru di Excel Anda (Data dan Pengetahuan\...)
# 2. Pratinjau — tidak menulis apa pun
python .claude\skills\unpad-env-data-cleaner\scripts\import_inbox.py

# 3. Kalau laporannya benar, terapkan
python .claude\skills\unpad-env-data-cleaner\scripts\import_inbox.py --terapkan

# 4. Bangun ulang dashboard (staging -> validate -> promote)
python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data

# 5. Setelah data baru terbukti benar, naikkan lantai pengaman
python .claude\skills\unpad-env-data-cleaner\scripts\validate.py --data data --update-baseline
```

## Periode terkunci

Januari–Juni 2026 (timbulan) dan April 2025–Juni 2026 (kecelakaan) dikunci, karena
**workbook aslinya hilang**. Data Mei–Juni 2026 — 208.586 kg timbulan dan 6 kasus
kecelakaan — hanya hidup di buku besar ini, di `data/*.json`, dan di
`Arsip Data Dashboard\`. Tidak ada tempat keempat.

## Yang tidak boleh dilakukan

- Jangan mengedit `*.csv` dengan tangan untuk **menghapus** baris. Catat koreksi
  sebagai baris baru, atau `git revert`. Menghapus tidak meninggalkan jejak.
- Jangan mengedit `*.md` — ia dihasilkan ulang dari CSV setiap impor.
- Jangan menjalankan parser yang sudah pensiun: `parse_timbulan.py`,
  `parse_timbulan_master.py`, `parse_traffic_accidents.py`,
  `parse_traffic_accidents_xlsx.py`, `update_timbulan_from_xlsx.py`,
  `update_traffic_from_xlsx.py`. Semuanya melewati buku besar.
