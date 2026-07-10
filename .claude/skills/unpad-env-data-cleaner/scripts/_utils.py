"""Shared utilities for UNPAD environmental data cleaning pipeline.

All functions stdlib-only. Path-safe on Windows.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = SKILL_ROOT / "resources"
SCHEMAS_DIR = SKILL_ROOT / "schemas"
DEFAULT_OUTPUT_DIR = SKILL_ROOT / "output"

SPEC_VERSION = "1.4"
GENERATED_AT_FALLBACK = "2026-05-14T10:00:00+07:00"


def now_iso() -> str:
    """ISO-8601 timestamp in WIB (+07:00). Deterministic for reproducibility flag."""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    """Convert label to kebab-case ASCII id."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    return text


def parse_number(value: str | int | float | None) -> float | int | None:
    """Parse Indonesian-formatted number ('1.234,56') or English ('1234.56') to float/int.

    Returns None for empty/missing.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    if not s or s in {"-", "—", ""}:
        return None
    # Strip bold markdown
    s = s.replace("**", "").strip()
    if not s:
        return None
    # Indonesian: 1.234,56 → 1234.56
    if "," in s:
        # Comma present → Indonesian convention; dots are thousand sep, comma is decimal
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        # Multiple dots → all thousand separators (e.g., 1.234.567)
        s = s.replace(".", "")
    elif "." in s:
        # Single dot, no comma. Disambiguate between Indonesian thousand sep
        # ("1.040" = 1040) and Excel-serialised decimal ("5916.3" = 5916.3).
        before, after = s.split(".")
        bs = before.lstrip("-")
        looks_like_thousand_sep = (
            len(after) == 3
            and bs.isdigit()
            and bs != "0"
        )
        if looks_like_thousand_sep:
            s = s.replace(".", "")
    try:
        n = float(s)
    except ValueError:
        return None
    return int(n) if n.is_integer() else n


def parse_pct(value: str | None) -> float | None:
    """Parse '3,03%' → 3.03."""
    if value is None:
        return None
    s = str(value).strip().rstrip("%").strip()
    return parse_number(s)


def fix_md_to_dm(date_str: str, sheet_hint: str | None = None) -> tuple[str, bool]:
    """Repair Excel M/D parsing applied to Indonesian D/M input.

    Returns (iso_date, was_corrected).

    Rule: if month <= 12 AND day <= 12, AND sheet_hint suggests the swapped reading
    matches the sheet's reported period, swap. Otherwise return as-is (D/M assumed).
    """
    s = date_str.strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if not m:
        # Try ISO
        try:
            d = date.fromisoformat(s)
            return d.isoformat(), False
        except ValueError:
            return s, False
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # As literally parsed (D/M): day=a, month=b
    day_dm, month_dm = a, b
    # As literally parsed if reversed (M/D was applied to D/M input):
    day_md, month_md = b, a

    swap = False
    if sheet_hint == "Des25":
        # Expect month=12. If month_dm != 12 but month_md == 12, swap.
        if month_dm != 12 and month_md == 12:
            swap = True
    elif sheet_hint == "Jan26":
        if y == 2026 and month_dm != 1 and month_md == 1:
            swap = True
    else:
        # Generic: cannot decide safely; trust D/M.
        swap = False

    if swap:
        day, month = day_md, month_md
    else:
        day, month = day_dm, month_dm
    try:
        d = date(y, month, day)
    except ValueError:
        return s, False
    return d.isoformat(), swap


def write_json(path: Path, data: Any) -> None:
    """Write JSON UTF-8 with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_md(path: Path) -> str:
    """Read a Markdown file as text."""
    return path.read_text(encoding="utf-8")


def base_dataset(dataset_id: str, source_files: list[str], period: dict[str, str]) -> dict[str, Any]:
    """Return the boilerplate top-level fields required by every dataset."""
    return {
        "dataset_id": dataset_id,
        "version": SPEC_VERSION,
        "generated_at": GENERATED_AT_FALLBACK,
        "source_files": source_files,
        "period": period,
        "data_quality_flags": [],
    }


def flag(severity: str, message: str) -> dict[str, str]:
    """Build a data_quality_flag entry."""
    if severity not in {"info", "warning", "error"}:
        raise ValueError(f"invalid severity {severity!r}")
    return {"severity": severity, "message": message}


def round_to(value: float, ndigits: int = 2) -> float:
    """Round preserving integer-when-possible semantics."""
    r = round(value, ndigits)
    return int(r) if r == int(r) and ndigits >= 0 else r


def find_project_root() -> Path:
    """Locate the project root (where data-spec.md lives)."""
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / "data-spec.md").exists():
            return parent
    return PROJECT_ROOT


DATA_DIRNAME = "Data dan Pengetahuan"


def find_source(filename: str, subdirs: tuple[str, ...] = ()) -> Path | None:
    """Cari file sumber di root project, lalu di folder 'Data dan Pengetahuan'.

    Sumber biner (.xlsx/.pdf) di-gitignore dan tidak pernah ada di root repo,
    melainkan di folder data milik user. Kembalikan None kalau tak ketemu —
    pemanggil wajib gagal keras, bukan melanjutkan dengan data kosong.
    """
    project = find_project_root()
    candidates = [project / filename]
    for base in (project.parent, project.parent.parent):
        candidates.append(base / DATA_DIRNAME / filename)
        candidates.extend(base / DATA_DIRNAME / sd / filename for sd in subdirs)
    for c in candidates:
        if c.exists():
            return c
    return None


ARSIP_DIRNAME = "arsip"


def find_archived_md(project: Path, filename: str) -> Path:
    """Cari MD sumber lama: 'arsip/' dulu, lalu root repo.

    Sejak 10 Juli 2026 sumber MD timbulan dan kecelakaan dipindahkan ke 'arsip/'
    karena data/_ledger/ sudah menggantikannya. Hanya parser PENSIUN yang
    memakainya, dan hanya untuk forensik. Root tetap dicoba supaya salinan lama
    di mesin siapa pun tetap terbaca.
    """
    for c in (project / ARSIP_DIRNAME / filename, project / filename):
        if c.exists():
            return c
    # Kembalikan jalur arsip supaya pesan galat menunjuk tempat yang benar.
    return project / ARSIP_DIRNAME / filename


def resolve_output(out_arg: str | None) -> Path:
    """Resolve --out flag relative to project root, default to skill output/."""
    if out_arg is None:
        return DEFAULT_OUTPUT_DIR
    p = Path(out_arg)
    if not p.is_absolute():
        p = find_project_root() / p
    return p
