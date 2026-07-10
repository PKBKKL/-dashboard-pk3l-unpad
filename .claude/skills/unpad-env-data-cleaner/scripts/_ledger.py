"""Kerangka buku besar (ledger) — sumber kebenaran append-only.

Buku besar berformat TEKS (CSV) supaya ikut git; *.xlsx di-gitignore, jadi
workbook Excel tidak pernah punya riwayat versi. Setiap baris yang masuk tidak
pernah keluar. Workbook Excel hanya kotak masuk: ia boleh MENAMBAH, tidak
pernah MENGURANGI.

Layout:
    data/_ledger/
      timbulan.csv                     fakta harian
      timbulan.md                      cermin bacaan (dihasilkan, jangan diedit)
      timbulan_kategori.csv            kamus
      timbulan_kendaraan.csv           kamus
      timbulan_tare.csv                kamus
      timbulan_flags.csv               data_quality_flags
      traffic_accidents.csv            fakta bulanan per jenis
      traffic_accidents_detail.csv     fakta per lokasi
      traffic_accidents.md
      traffic_accidents_jenis.csv      kamus
      traffic_accidents_flags.csv
      _peta_kolom.csv                  pola header -> kategori, berlaku-sejak
      _terkunci.csv                    periode yang tidak boleh diubah
      _konflik/YYYY-MM-DD.md           laporan konflik tiap impor

Buku besar adalah SUMBER, bukan keluaran. Ia tinggal di data/_ledger/ dan
dibaca parser; ia tidak pernah ditulis oleh run_all.py.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from _utils import find_project_root

LEDGER_DIRNAME = "_ledger"
ABAIKAN = "__ABAIKAN__"


def ledger_dir(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    return find_project_root() / "data" / LEDGER_DIRNAME


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_rows(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})


def num(v) -> float:
    """CSV menyimpan teks. Kosong = 0."""
    if v is None or v == "":
        return 0.0
    return float(v)


def fmt(v: float) -> str:
    """Tulis 7430.0 sebagai '7430', 3112.33 tetap '3112.33'."""
    r = round(float(v), 3)
    return str(int(r)) if r == int(r) else str(r)


def same(a, b) -> bool:
    return abs(num(a) - num(b)) < 1e-6


# ── Penguncian periode ───────────────────────────────────────────────────

FREEZE_FIELDS = ["dataset", "periode_awal", "periode_akhir", "dikunci_pada", "alasan"]


def load_freeze(led: Path) -> list[dict]:
    return read_rows(led / "_terkunci.csv")


def is_frozen(freeze: list[dict], dataset: str, month_iso: str) -> dict | None:
    """month_iso = 'YYYY-MM'. Kembalikan baris penguncian kalau terkunci."""
    for f in freeze:
        if f["dataset"] != dataset:
            continue
        if f["periode_awal"] <= month_iso <= f["periode_akhir"]:
            return f
    return None


# ── Peta kolom (pola header → kategori, berlaku-sejak-tanggal) ───────────

PETA_FIELDS = ["prioritas", "pola", "cocok", "kategori", "berlaku_sejak", "berlaku_sampai", "catatan"]


def load_peta(led: Path) -> list[dict]:
    rows = read_rows(led / "_peta_kolom.csv")
    return sorted(rows, key=lambda r: int(r["prioritas"]))


def _cocok(pola: str, cocok: str, label: str) -> bool:
    lab, pol = label.strip().lower(), pola.strip().lower()
    if cocok == "exact":
        return lab == pol
    if cocok == "awalan":
        return lab.startswith(pol)
    return pol in lab


def match_kategori(label: str, tanggal_iso: str, peta: list[dict]) -> str | None:
    """Kembalikan kategori, ABAIKAN, atau None kalau tidak dikenali.

    Diurut menurut `prioritas` — yang pertama cocok menang. Ini penting:
    'SOD RS (Pick Up)' harus jadi sisa_makanan, bukan lingkungan.
    """
    for r in peta:
        if not _cocok(r["pola"], r["cocok"], label):
            continue
        sejak, sampai = r.get("berlaku_sejak") or "", r.get("berlaku_sampai") or ""
        if sejak and tanggal_iso < sejak:
            continue
        if sampai and tanggal_iso > sampai:
            continue
        return r["kategori"]
    return None


# ── Cermin Markdown ──────────────────────────────────────────────────────


def write_md_mirror(csv_path: Path, md_path: Path, judul: str, catatan: str) -> None:
    rows = read_rows(csv_path)
    lines = [
        f"# {judul}", "",
        "> **Cermin bacaan buku besar. Dihasilkan otomatis — jangan diedit.**  ",
        f"> Sumber kebenaran: `{csv_path.name}`. {catatan}", "",
        f"_{len(rows)} baris_", "",
    ]
    if rows:
        cols = list(rows[0].keys())
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join("---" for _ in cols) + "|")
        for r in rows:
            lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "\\|") for c in cols) + " |")
    else:
        lines.append("_(kosong)_")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Laporan konflik ──────────────────────────────────────────────────────


def write_conflict_report(led: Path, tanggal: str, bagian: dict[str, list[str]]) -> Path | None:
    isi = [f"## Laporan Impor — {tanggal}", ""]
    ada = False
    for judul, baris in bagian.items():
        isi += [f"### {judul}", ""]
        if baris:
            ada = True
            isi += [f"- {b}" for b in baris]
        else:
            isi.append("_(tidak ada)_")
        isi.append("")
    if not ada:
        return None
    path = led / "_konflik" / f"{tanggal}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(isi), encoding="utf-8")
    return path


def today_iso() -> str:
    return date.today().isoformat()
