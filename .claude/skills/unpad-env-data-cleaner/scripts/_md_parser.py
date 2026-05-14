"""Markdown table parser.

Extracts GitHub-flavored Markdown tables from a string and returns them as
list[dict] groups, preserving table order and the surrounding section headings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MDTable:
    headers: list[str]
    rows: list[list[str]]
    section_path: list[str] = field(default_factory=list)
    starts_at_line: int = 0

    def as_dicts(self) -> list[dict[str, str]]:
        """Return rows as list of dicts keyed by header.

        Duplicate header names get suffixed _2, _3, etc.
        """
        unique_headers: list[str] = []
        seen: dict[str, int] = {}
        for h in self.headers:
            key = h.strip()
            if key in seen:
                seen[key] += 1
                unique_headers.append(f"{key}__{seen[key]}")
            else:
                seen[key] = 1
                unique_headers.append(key)
        return [
            {unique_headers[i]: (row[i] if i < len(row) else "") for i in range(len(unique_headers))}
            for row in self.rows
        ]


def _is_separator(line: str) -> bool:
    """Detect the | --- | --- | row that follows the header row."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if not cells:
        return False
    return all(re.fullmatch(r":?-+:?", c) for c in cells)


def _split_row(line: str) -> list[str]:
    """Split a | a | b | c | row into cell values."""
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


def parse_md(md_text: str) -> list[MDTable]:
    """Return all GFM tables found in md_text, tagged with their section heading path."""
    lines = md_text.splitlines()
    tables: list[MDTable] = []
    section_stack: list[tuple[int, str]] = []  # (level, title)
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Track headings to attach context to tables.
        h = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if h:
            level = len(h.group(1))
            title = h.group(2).strip()
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            section_stack.append((level, title))
            i += 1
            continue
        # Detect table start: header row + separator on next line.
        if line.strip().startswith("|") and i + 1 < n and _is_separator(lines[i + 1]):
            headers = _split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                if _is_separator(lines[i]):
                    i += 1
                    continue
                rows.append(_split_row(lines[i]))
                i += 1
            tables.append(MDTable(
                headers=headers,
                rows=rows,
                section_path=[t for _, t in section_stack],
                starts_at_line=i - len(rows) - 2,
            ))
            continue
        i += 1
    return tables


def find_tables(md_text: str, section_contains: str | None = None) -> list[MDTable]:
    """Filter parsed tables by a substring in any section heading on the path."""
    all_tables = parse_md(md_text)
    if section_contains is None:
        return all_tables
    needle = section_contains.lower()
    return [t for t in all_tables if any(needle in s.lower() for s in t.section_path)]
