# Arsip — sumber Markdown yang sudah digantikan buku besar

Berkas di folder ini **bukan sumber data lagi**. Pipeline aktif (`run_all.py`) tidak pernah
membacanya. Mereka disimpan untuk forensik dan jejak sejarah, bukan untuk dipakai.

Dipindahkan ke sini pada **10 Juli 2026**, ketika `data/_ledger/` menjadi sumber kebenaran
untuk timbulan dan kecelakaan lalu lintas.

| Berkas | Digantikan oleh | Dibaca oleh (pensiun) |
|---|---|---|
| `Total Timbulan Sampah 2026  (Bulanan).md` | `data/_ledger/timbulan.csv` | `parse_timbulan.py` |
| `Kecelakaan Lalu Lintas.md` | `data/_ledger/traffic_accidents.csv` | `parse_traffic_accidents.py` |

## Kenapa diarsipkan, bukan dipakai

Bukan sekadar soal kerapian. **Kedua MD ini memuat data yang lebih sedikit daripada dashboard.**

Timbulan, dibuktikan dengan menjalankan `parse_timbulan.py --i-know-this-is-retired`
dan membandingkannya dengan `data/timbulan.json`:

| Bulan 2026 | MD arsip | Buku besar |
|---|---:|---:|
| Januari | 15.170 kg | 15.170 kg |
| Februari | 99.644 kg | **101.299 kg** |
| Maret | 43.160 kg | **50.189 kg** |
| April | 120.544 kg | **123.574 kg** |
| Mei | 0 | **115.216 kg** |
| Juni | 0 | **93.370 kg** |
| **Total** | **278.518 kg** | **498.818 kg** |

Selisih Februari–April berasal dari kolom `Total` di workbook asal yang tidak dapat dipercaya:
ia hanya menjumlahkan Tim Angsa, melewatkan SOD RS dan Pick Up. Mei dan Juni tidak pernah
tercatat di MD sama sekali — workbook yang menghasilkannya **hilang permanen**, dan JSON
dashboard sempat menjadi satu-satunya salinan angka itu.

Karena itu periode Januari–Juni 2026 **dikunci** di `data/_ledger/_terkunci.csv`.

Kecelakaan lalu lintas mengalami hal serupa: MD arsip hanya memuat 4 kasus untuk 2026,
sedangkan buku besar memuat 10.

## Kalau Anda perlu membacanya lagi

Parser pensiun masih bisa dijalankan untuk forensik dan akan mencari berkasnya di sini:

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\parse_timbulan.py `
    --i-know-this-is-retired --out <folder-sementara>
```

**Jangan pernah** mengarahkan keluarannya ke `data/`. Ia akan memangkas 220.300 kg.
