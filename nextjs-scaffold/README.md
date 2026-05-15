# Next.js Scaffold (Arsip)

Scaffold Next.js 15 + Tailwind + Recharts untuk Dashboard Pemantauan Lingkungan PKBKKL UNPAD.

> **Status: ARSIP — tidak dipakai untuk produksi.**
> Dashboard yang aktif di-deploy: **Streamlit Cloud** (`streamlit_app.py`) dan **Netlify HTML statis** (`docs/`). Scaffold ini disimpan sebagai alternatif eksperimental kalau suatu saat ingin pindah ke React/Next.js.

## Cara jalankan lokal

```powershell
cd nextjs-scaffold
npm install
npm run dev
```

Buka <http://localhost:3000>.

## Catatan

- Data dibaca dari `../data/` (folder canonical di root repo)
- Scaffold ini tidak ikut polish terbaru di HTML statis (logo dual UNPAD+PKBKKL, split chart timbulan, hapus catatan integritas data, dll.). Kalau memang mau dipakai, perlu porting ulang dari `docs/`.
