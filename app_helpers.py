"""Shared helpers for the Streamlit dashboard.

All data is loaded from data/*.json (output of unpad-env-data-cleaner skill).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


# ─── Data loaders (cached) ────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_meta() -> dict[str, Any]:
    return _read_json(DATA_DIR / "meta.json")


@st.cache_data(show_spinner=False)
def load_dataset(name: str) -> dict[str, Any]:
    return _read_json(DATA_DIR / f"{name}.json")


@st.cache_data(show_spinner=False)
def load_shared(name: str) -> dict[str, Any]:
    return _read_json(DATA_DIR / "shared" / f"{name}.json")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ─── Formatting helpers (id-ID locale) ────────────────────────────────────

def fmt_int(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{int(round(v)):,}".replace(",", ".")


def fmt_kg(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(v):,} kg".replace(",", ".")


def fmt_num(v: float | int | None, decimals: int = 2) -> str:
    if v is None:
        return "—"
    s = f"{v:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%".replace(".", ",")


def fmt_month(iso_month: str) -> str:
    try:
        y, m = iso_month.split("-")
        return f"{MONTHS_ID[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return iso_month


def fmt_threshold(t: dict | None) -> str:
    if not t:
        return "—"
    tt = t.get("type")
    if tt == "max":
        return f"≤ {fmt_num(t.get('max'), 3)}"
    if tt == "min":
        return f"≥ {fmt_num(t.get('min'), 3)}"
    if tt == "range":
        return f"{fmt_num(t.get('min'), 1)} – {fmt_num(t.get('max'), 1)}"
    if tt == "deviation":
        return f"dev ±{fmt_num(t.get('max_dev'), 0)}"
    if tt == "qualitative":
        return t.get("expected", "kualitatif")
    return "—"


# ─── Color palette ────────────────────────────────────────────────────────

def get_palette() -> dict[str, str]:
    return load_meta()["color_palette"]


def status_color(compliant: bool | None) -> str:
    p = get_palette()
    if compliant is True:
        return p["compliant"]
    if compliant is False:
        return p["exceedance"]
    return p["below_detection"]


# ─── Common UI patterns ───────────────────────────────────────────────────

def render_flags(flags: list[dict], title: str = "Catatan Integritas Data") -> None:
    if not flags:
        return
    st.markdown(f"#### {title}")
    for f in flags:
        sev = f.get("severity", "info")
        msg = f.get("message", "")
        if sev == "info":
            st.info(msg)
        elif sev == "warning":
            st.warning(msg)
        elif sev == "error":
            st.error(msg)
        else:
            st.write(msg)


def page_header(title: str, period: str | None = None, description: str | None = None) -> None:
    """Render a uniform page header."""
    if period:
        st.markdown(
            f"## {title} "
            f"<span style='font-size: 0.65em; background: #f1f5f9; color: #475569; "
            f"border-radius: 999px; padding: 0.2em 0.7em; vertical-align: middle; "
            f"margin-left: 0.4em;'>{period}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"## {title}")
    if description:
        st.markdown(
            f"<p style='color: #475569; line-height: 1.6; max-width: 900px;'>{description}</p>",
            unsafe_allow_html=True,
        )
    st.divider()


def configure_page(title: str) -> None:
    """Standard page configuration. Call as the first command in each page."""
    st.set_page_config(
        page_title=f"{title} · PKBKKL UNPAD",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": "Dashboard Pemantauan Lingkungan PKBKKL Universitas Padjadjaran",
        },
    )
