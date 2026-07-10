"""Periksa sintaks JavaScript seluruh halaman docs/*.html tanpa Node.

Latar: 10 Juli 2026 satu kurung tutup liar di `docs/limbah-b3.html` membuat
<script type="module"> gagal di-parse. SyntaxError pada ES module membatalkan
SELURUH modul, jadi halaman itu terbit ke publik dalam keadaan kosong total.
`node` tidak terpasang di mesin pemilik, dan pemeriksa kurung buatan sendiri
memberi false positive pada regex literal serta template bersarang.

Skrip ini memakai tree-sitter — parser JavaScript sungguhan.

Pakai:
    python check_frontend.py                 # periksa semua docs/*.html
    python check_frontend.py docs/limbah-b3.html

Keluar dengan kode 1 bila ada node ERROR/MISSING. Jalankan SEBELUM commit
apa pun yang menyentuh docs/*.html.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _utils import find_project_root

SCRIPT_RE = re.compile(r'<script[^>]*type="module"[^>]*>(.*?)</script>', re.S)


def _muat_parser():
    try:
        import tree_sitter_javascript as tsjs
        from tree_sitter import Language, Parser
    except ImportError:
        print(
            "[check_frontend] tree-sitter belum terpasang. Jalankan:\n"
            "    python -m pip install tree-sitter tree-sitter-javascript",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return Parser(Language(tsjs.language()))


def _kumpulkan_error(node, keluar):
    if node.type == "ERROR" or node.is_missing:
        keluar.append(node)
    for anak in node.children:
        _kumpulkan_error(anak, keluar)


def periksa(path: Path, parser) -> list[str]:
    """Kembalikan daftar pesan masalah. Kosong berarti bersih."""
    html = path.read_text(encoding="utf-8")
    modul = SCRIPT_RE.search(html)
    if not modul:
        return []  # halaman tanpa <script type="module"> — tidak apa-apa
    src = modul.group(1)
    # Berapa baris HTML sebelum isi modul, supaya nomor baris cocok dengan editor.
    offset = html[: modul.start(1)].count("\n")

    tree = parser.parse(src.encode("utf-8"))
    errs: list = []
    _kumpulkan_error(tree.root_node, errs)

    baris = src.splitlines()
    pesan = []
    for e in errs:
        n = e.start_point[0]
        jenis = "MISSING" if e.is_missing else "ERROR"
        cuplikan = baris[n].strip()[:90] if n < len(baris) else ""
        pesan.append(f"{path.name}:{offset + n + 1} [{jenis}] {cuplikan}")
    return pesan


def main() -> int:
    parser = _muat_parser()
    if len(sys.argv) > 1:
        berkas = [Path(a) for a in sys.argv[1:]]
    else:
        berkas = sorted((find_project_root() / "docs").glob("*.html"))
    if not berkas:
        print("[check_frontend] tidak ada berkas untuk diperiksa", file=sys.stderr)
        return 1

    total = 0
    for p in berkas:
        if not p.exists():
            print(f"[check_frontend] tidak ditemukan: {p}", file=sys.stderr)
            return 1
        masalah = periksa(p, parser)
        total += len(masalah)
        status = "bersih" if not masalah else f"{len(masalah)} MASALAH"
        print(f"[check_frontend] {p.name:<28} {status}")
        for m in masalah:
            print(f"    {m}")

    if total:
        print(
            f"\n[check_frontend] GAGAL: {total} masalah sintaks. "
            f"SyntaxError pada ES module membuat halaman kosong total, bukan rusak sebagian.",
            file=sys.stderr,
        )
        return 1
    print(f"\n[check_frontend] {len(berkas)} halaman parse bersih.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
