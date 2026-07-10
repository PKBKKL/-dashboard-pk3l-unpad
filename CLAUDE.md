# Dashboard Pemantauan Lingkungan PKBKKL UNPAD

Dashboard publik yang dipakai sebagai rekam jejak resmi pemantauan lingkungan Universitas
Padjadjaran. Angka yang salah atau hilang di sini merusak auditabilitas, dan sebagian di
antaranya (kode limbah B3) punya konsekuensi hukum.

Live: <https://pkbkkl.github.io/-dashboard-pk3l-unpad/>

---

## Dua jaminan yang tidak boleh dilanggar

Ditetapkan pemilik dashboard:

1. **Deploy ulang tidak boleh mengubah data lama.**
2. **Menambah data baru tidak boleh menghilangkan data lama.**

Segala sesuatu di bawah ini ada untuk menegakkan dua kalimat itu.

---

## Sepuluh hukum besi

1. **`Data dan Pengetahuan\` adalah kotak masuk, BACA-SAJA.** Jangan pernah menulis ke sana.
   Workbook pemilik menyimpan berat sebagai rumus (`=5550-4020`, bruto − tara); menyimpannya
   ulang lewat `openpyxl` membuang nilai ter-cache dan sel terbaca kosong.

2. **Buku besar `data\_ledger\` adalah sumber kebenaran.** Ia append-only. Baris lama tidak
   pernah diubah atau dihapus. Excel hanya boleh *menambah*.

3. **Tidak ada kehilangan senyap.** Apa pun yang dibuang harus menjadi `data_quality_flags`
   atau menghentikan build. Satuan tak dikenal, kolom tak terpetakan, rumus tanpa nilai
   ter-cache — semuanya **gagal-keras**.

4. **Jangan mengoreksi data pemilik diam-diam.** Tanggal janggal, duplikat, satuan yang tidak
   cocok dengan kategori: terbitkan sebagai peringatan, jangan diperbaiki sendiri.

5. **Periode terkunci tidak boleh berubah.** Lihat `data\_ledger\_terkunci.csv`. Sumber asli
   periode itu sudah hilang; JSON dashboard satu-satunya salinan.

6. **Promosi hanya menyalin, tidak pernah menghapus.** Karena itu `water_quality_ip.json`
   (tidak punya parser) selalu selamat dari `run_all.py`.

7. **Penyusutan = error, bukan peringatan.** `data\_baseline.json` menahan promosi bila jumlah
   entri atau total mana pun berkurang.

8. **Buktikan, jangan klaim.** Setiap pernyataan angka harus berasal dari perintah yang
   benar-benar dijalankan. Bandingkan sebelum-sesudah, jangan mengandalkan ingatan.

9. **Kode limbah B3 punya konsekuensi hukum.** Kode berstatus `usulan` tidak boleh disamarkan
   menjadi resmi. Provenance ada di `kode_status`, bukan di besar-kecil huruf.

10. **Frontend wajib lolos `check_frontend.py` sebelum commit.** `SyntaxError` pada
    `<script type="module">` mengosongkan **seluruh** halaman, bukan sebagiannya.

---

## Arsitektur tiga lapis

```
Kotak masuk   Data dan Pengetahuan\*.xlsx        milik pemilik, baca-saja bagi mesin
     |  import_inbox.py  (append-only, dry-run bawaan)
Buku besar    data\_ledger\*.csv                 sumber kebenaran, ikut git
     |  parser  (staging -> validate -> promote)
Terbitan      data\*.json -> docs\data\*.json    boleh dibangun ulang kapan saja
     |
Streamlit (streamlit_app.py + pages\)   ·   HTML statis (docs\, GitHub Pages)
```

Buku besar baru dipakai **timbulan** dan **traffic_accidents**. Empat dataset lain
(`pengolahan_sampah`, `water_quality`, `tree_incidents`, `b3_waste`) masih dibaca langsung
dari MD/XLSX. `water_quality_ip` tidak punya parser sama sekali — jangan menulis satu pun
tanpa memastikan tahun 2024 dan 2025 tetap ada di keluarannya.

`b3_waste` punya kamus kode ber-provenance di `data\_ledger\b3_waste_kode.csv`. Kamus hanya
dipakai bila sel `Kode Limbah` di Excel **kosong**; Excel selalu menang.

---

## Urutan kerja rutin

Jangan melompati langkah.

```powershell
$S = ".claude\skills\unpad-env-data-cleaner\scripts"

python $S\import_inbox.py                      # dry-run, tidak menulis apa pun
# tunjukkan laporannya ke pemilik, tunggu persetujuan
python $S\import_inbox.py --terapkan

python $S\run_all.py --out data                # staging -> validate -> promote
python $S\check_frontend.py                    # WAJIB bila docs\*.html disentuh

# hanya setelah data baru terbukti benar:
python $S\validate.py --data data --update-baseline

python $S\publish_docs.py                      # data\ -> docs\data\, menolak berkas kerja

# tunjukkan selisih angkanya, tunggu izin, baru commit + push
```

Exit code `run_all.py` / `validate.py`: `0` lulus · `1` error (termasuk regresi) · `2` warning.

**Jangan pernah** memakai `--skip-validate`, `--allow-regression`, atau
`--i-know-this-is-retired` atas inisiatif sendiri.

---

## Agent

Definisi agent ada di `.claude\agents\`. Serahkan pekerjaan pada yang paling sempit
kewenangannya:

| Agent | Peran |
|---|---|
| `pk3l-coordinator` | Manajer; mendelegasikan ke sepuluh agent di bawah |
| `pk3l-inspector` | Baca-saja. Membaca Excel/PDF/JSON, menghasilkan laporan dry-run. Tidak pernah menulis |
| `pk3l-ledger-keeper` | Satu-satunya yang boleh menulis ke `data\_ledger\` |
| `pk3l-pipeline-guard` | Menjalankan `run_all.py`, memblokir promosi bila data menyusut |
| `pk3l-deployer` | Menyalin ke `docs\data\`, commit, push, memverifikasi situs live |
| `pk3l-timbulan` `pk3l-pengolahan` `pk3l-kualitas-air` `pk3l-vegetasi` `pk3l-kecelakaan` `pk3l-limbah-b3` | Spesialis per dataset: analisis, olah, tulis kode |

---

## Jebakan yang sudah pernah termakan

- **Satuan ditebak dari teks.** `satuan.startsWith("liter")` membuang seluruh entri
  `"Mili Liter"` — 15 entri, 2,485 L, termasuk 300 mL sianida. Satuan kini dinormalkan
  sekali di parser dan diterbitkan sebagai `volume_liter` / `mass_kg` per entri.
- **Kurung tutup liar.** Mengganti blok `if/else if` tanpa membuang `}` milik `else`
  membuat halaman Limbah B3 terbit dalam keadaan kosong total.
- **Kolom hardcoded per bulan.** Parser timbulan lama memetakan kolom Excel per bulan;
  menambah Juli berarti bulan itu hilang diam-diam. Kini pemetaan berbasis label header.
- **`node` tidak terpasang** di mesin pemilik dan tidak ada di mana pun. Jangan mengandalkan
  `node --check`. Pakai `check_frontend.py` (tree-sitter).
- **Kloning meng-checkout CRLF, berkas lokal LF.** Perbandingan `cmp`/`md5` akan menyesatkan;
  percayai `git status`, atau normalkan `\r\n` sebelum membandingkan.
- **`data\*` bukan isi `docs\data\`.** `_baseline.json` dan `_ledger\` ikut git di `data\`,
  tetapi **tidak** boleh diterbitkan ke `docs\data\`. Bahkan `Copy-Item data\*.json docs\data\`
  pun salah — `_baseline.json` berakhiran `.json`. Pakai `publish_docs.py`, yang menolak
  segala berkas berawalan garis bawah dan memverifikasi hasilnya.
