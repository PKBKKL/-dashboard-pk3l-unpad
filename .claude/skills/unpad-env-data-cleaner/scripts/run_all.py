"""Orchestrator — jalankan semua parser, validasi, baru promosikan.

Alur aman (staging → validate → promote):
  1. Semua parser menulis ke folder singgah sementara, BUKAN ke data/.
  2. Hasil singgah ditumpangkan di atas isi data/ yang sekarang → 'preview'.
  3. validate.py memeriksa preview, termasuk pengaman anti-regresi.
  4. Kalau ada error, data/ TIDAK DISENTUH sama sekali. Proses berhenti.
  5. Kalau lolos, file dari singgah disalin ke data/.

Dengan begitu rebuild yang menghilangkan data tidak pernah sampai ke disk.
File yang tidak dihasilkan pipeline (mis. water_quality_ip.json) tidak pernah
terhapus, karena promosi hanya menyalin, tidak pernah mengosongkan folder.

Usage:
  python run_all.py --out data
  python run_all.py --out data --skip-validate      # BAHAYA: promosi tanpa cek
  python run_all.py --out data --allow-regression   # BAHAYA: promosi walau data berkurang
  python run_all.py                                 # ke output/ milik skill
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from _utils import resolve_output  # noqa: E402

PIPELINE = [
    "build_shared",
    "build_meta",
    "parse_pengolahan_sampah",
    # Sumber resmi timbulan & kecelakaan adalah BUKU BESAR di data/_ledger/ —
    # append-only, berformat teks, ikut git. Workbook Excel hanya kotak masuk;
    # ia menambah baris lewat import_inbox.py dan tidak pernah bisa mengurangi.
    # Parser MD lama dan parser XLSX langsung sudah dikeluarkan dari sini.
    "parse_timbulan_ledger",
    "parse_water_quality",
    "parse_tree_incidents",
    "parse_traffic_accidents_ledger",
    "parse_b3_waste",
    "parse_electricity",
]


def _copy_tree(src: Path, dst: Path) -> list[Path]:
    """Salin isi src ke dst (menimpa file senama, tidak menghapus yang lain)."""
    written: list[Path] = []
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        written.append(target)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full UNPAD env data cleaning pipeline.")
    ap.add_argument("--out", default=None, help="Output dir (default: skill output/)")
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--allow-regression", action="store_true",
                    help="Promosikan walau data berkurang dari baseline. Hanya untuk penurunan yang disengaja.")
    args = ap.parse_args()

    final_out = resolve_output(args.out)

    with tempfile.TemporaryDirectory(prefix="unpad_staging_") as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir(parents=True)

        for step in PIPELINE:
            print(f"\n=== {step} ===")
            cmd = [sys.executable, str(THIS_DIR / f"{step}.py"), "--out", str(staging)]
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                print(f"\n[run_all] step {step} gagal (kode {result.returncode}).", file=sys.stderr)
                print(f"[run_all] {final_out} TIDAK diubah.", file=sys.stderr)
                return result.returncode

        if args.skip_validate:
            print("\n[run_all] validasi dilewati (--skip-validate) — promosi langsung.")
            written = _copy_tree(staging, final_out)
            print(f"[run_all] {len(written)} file dipromosikan ke {final_out}")
            return 0

        # Preview = isi data/ sekarang, ditimpa hasil singgah.
        preview = Path(tmp) / "preview"
        preview.mkdir(parents=True)
        if final_out.exists():
            _copy_tree(final_out, preview)
        _copy_tree(staging, preview)

        print("\n=== validate (pada hasil gabungan, sebelum promosi) ===")
        cmd = [sys.executable, str(THIS_DIR / "validate.py"), "--data", str(preview)]
        if args.allow_regression:
            cmd.append("--skip-regression")
        rc = subprocess.run(cmd, check=False).returncode

        if rc == 1:
            print("\n" + "=" * 72, file=sys.stderr)
            print("[run_all] VALIDASI GAGAL — promosi DIBATALKAN.", file=sys.stderr)
            print(f"[run_all] {final_out} tidak disentuh sama sekali.", file=sys.stderr)
            print("[run_all] Periksa file sumber. Kalau penurunan data memang disengaja,", file=sys.stderr)
            print("[run_all]   perbarui baseline dulu:  validate.py --data data --update-baseline", file=sys.stderr)
            print("=" * 72, file=sys.stderr)
            return 1

        written = _copy_tree(staging, final_out)
        print(f"\n[run_all] validasi lolos (kode {rc}) — {len(written)} file dipromosikan ke {final_out}")
        if rc == 2:
            print("[run_all] ada warning; periksa pesan di atas sebelum commit.")
        return rc


if __name__ == "__main__":
    sys.exit(main())
