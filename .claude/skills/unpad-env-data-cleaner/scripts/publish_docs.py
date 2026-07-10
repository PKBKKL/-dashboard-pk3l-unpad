"""Terbitkan data/ ke docs/data/ — hanya berkas yang memang boleh publik.

Kenapa ini ada, alih-alih satu baris Copy-Item:

    Copy-Item data\\*.json docs\\data\\ -Force

Perintah itu tampak benar tetapi ikut menyalin `_baseline.json`, karena namanya
memang berakhiran `.json`. Dan versi rekursifnya (`data\\* -Recurse`) ikut membawa
seluruh buku besar `_ledger\\` ke folder yang disajikan GitHub Pages ke publik.

`data/` memuat dua jenis berkas:
  - TERBITAN  : dataset JSON + shared/  -> boleh publik
  - KERJA     : _baseline.json, _ledger/ -> ikut git, TIDAK boleh publik

Aturan itu terlalu mudah dilanggar untuk dititipkan pada prosa di README.
Skrip ini menegakkannya: apa pun yang namanya diawali garis bawah ditolak.

Pakai:
    python publish_docs.py            # salin, lalu verifikasi
    python publish_docs.py --periksa  # hanya verifikasi, tidak menyalin
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import find_project_root

# Diawali garis bawah = berkas kerja, bukan terbitan. Jangan pernah publik.
PRIVAT = "_"


def _berkas_terbitan(data_dir: Path) -> list[Path]:
    return sorted(
        p for p in data_dir.glob("*.json") if not p.name.startswith(PRIVAT)
    )


def _shared(data_dir: Path) -> list[Path]:
    d = data_dir / "shared"
    return sorted(d.glob("*.json")) if d.is_dir() else []


def salin(data_dir: Path, docs_dir: Path) -> int:
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "shared").mkdir(exist_ok=True)

    n = 0
    for src in _berkas_terbitan(data_dir):
        shutil.copy2(src, docs_dir / src.name)
        n += 1
    for src in _shared(data_dir):
        shutil.copy2(src, docs_dir / "shared" / src.name)
        n += 1
    return n


def periksa(data_dir: Path, docs_dir: Path) -> list[str]:
    """Kembalikan daftar masalah. Kosong berarti terbitan sehat."""
    masalah: list[str] = []

    # 1. Tidak boleh ada berkas kerja yang bocor ke docs/.
    for p in docs_dir.iterdir():
        if p.name.startswith(PRIVAT):
            masalah.append(
                f"BOCOR: {p.name} ada di docs/data/. Berkas kerja tidak boleh publik."
            )

    # 2. Setiap terbitan harus ada dan identik.
    for src in _berkas_terbitan(data_dir):
        dst = docs_dir / src.name
        if not dst.exists():
            masalah.append(f"HILANG: {src.name} tidak ada di docs/data/.")
        elif not filecmp.cmp(src, dst, shallow=False):
            masalah.append(f"BEDA: {src.name} berbeda antara data/ dan docs/data/.")

    for src in _shared(data_dir):
        dst = docs_dir / "shared" / src.name
        if not dst.exists():
            masalah.append(f"HILANG: shared/{src.name} tidak ada di docs/data/.")
        elif not filecmp.cmp(src, dst, shallow=False):
            masalah.append(f"BEDA: shared/{src.name} berbeda.")

    # 3. Tidak boleh ada terbitan yatim di docs/ yang sudah tak ada di data/.
    #    (Bukan error keras: promosi tak pernah menghapus, tapi layak diketahui.)
    nama_data = {p.name for p in _berkas_terbitan(data_dir)}
    for p in sorted(docs_dir.glob("*.json")):
        if p.name not in nama_data and not p.name.startswith(PRIVAT):
            masalah.append(
                f"YATIM: docs/data/{p.name} tidak punya pasangan di data/. "
                f"Sengaja? (mis. dataset tanpa parser)"
            )
    return masalah


def main() -> int:
    ap = argparse.ArgumentParser(description="Terbitkan data/ ke docs/data/.")
    ap.add_argument("--periksa", action="store_true", help="hanya verifikasi")
    args = ap.parse_args()

    project = find_project_root()
    data_dir = project / "data"
    docs_dir = project / "docs" / "data"

    if not data_dir.is_dir():
        print(f"[publish_docs] tidak ada: {data_dir}", file=sys.stderr)
        return 1

    if not args.periksa:
        n = salin(data_dir, docs_dir)
        ditolak = [p.name for p in data_dir.glob("_*")]
        print(f"[publish_docs] {n} berkas disalin ke {docs_dir}")
        if ditolak:
            print(f"[publish_docs] tidak diterbitkan (berkas kerja): {', '.join(sorted(ditolak))}")

    masalah = periksa(data_dir, docs_dir)
    if masalah:
        print(f"[publish_docs] GAGAL: {len(masalah)} masalah", file=sys.stderr)
        for m in masalah:
            print(f"    {m}", file=sys.stderr)
        return 1

    print("[publish_docs] terbitan sehat: docs/data/ cocok dengan data/, tanpa berkas kerja.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
