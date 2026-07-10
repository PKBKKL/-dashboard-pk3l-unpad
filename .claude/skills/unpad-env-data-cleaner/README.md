# unpad-env-data-cleaner

Claude Code skill yang membangun **tujuh dataset JSON** pemantauan lingkungan UNPAD dari buku besar `data/_ledger/`, tiga berkas MD di root, dan logbook Excel limbah B3.

Kontrak keluaran: `data-spec.md` **v1.4**. Aturan wajib sebelum menyentuh apa pun: `CLAUDE.md` di root repo.

## Quick start

Dari root project:

```powershell
python .claude\skills\unpad-env-data-cleaner\scripts\run_all.py --out data
```

Output di `data/*.json` + `data/shared/*.json`.

## File penting untuk manusia

| File | Untuk apa |
|---|---|
| `SKILL.md` | Instruksi yang dibaca Claude saat skill dipakai. |
| `data-spec.md` (di root project) | Kontrak schema versi 1.0. |
| `scripts/_utils.py` | Helper bersama (date fix, slug, IO). |
| `scripts/parse_*.py` | Parser per-dataset. |
| `scripts/validate.py` | Cek invariant + cross-reference. |
| `schemas/*.schema.json` | JSON Schema Draft 2020-12. |
| `resources/locations_master.json` | Sumber kebenaran kamus lokasi. |
| `resources/regulations_master.json` | Kamus baku mutu. |
| `resources/parameter_thresholds.json` | Mapping parameter air → threshold direction. |

## Update workflow

- **Edit MD sumber** → `python scripts\run_all.py --out data`
- **Tambah lokasi baru** → edit `resources/locations_master.json` → jalankan ulang
- **Tambah parameter air** → edit `resources/parameter_thresholds.json` + `scripts/parse_water_quality.py:PARAMETER_LABEL_TO_ID`
- **Naik versi spec** → edit `data-spec.md` § Changelog, sinkronkan `_utils.py:SPEC_VERSION` dan `schemas/*`

## Exit codes

- `0` lulus
- `1` ada error (build harus dihentikan)
- `2` ada warning (dashboard bisa di-build, beri tahu user)
