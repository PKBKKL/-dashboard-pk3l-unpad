// Formatting helpers — all Indonesian locale.

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

const NF_INT = new Intl.NumberFormat("id-ID");
const NF_DEC = new Intl.NumberFormat("id-ID", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const NF_PCT = new Intl.NumberFormat("id-ID", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function fmtKg(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (Number.isInteger(value)) return `${NF_INT.format(value)} kg`;
  return `${NF_DEC.format(value)} kg`;
}

export function fmtNum(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return NF_DEC.format(value);
}

export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return NF_INT.format(value);
}

export function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${NF_PCT.format(value)}%`;
}

const MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];

export function fmtMonth(isoMonth: string): string {
  const [y, m] = isoMonth.split("-");
  const idx = parseInt(m, 10) - 1;
  if (idx < 0 || idx > 11) return isoMonth;
  return `${MONTHS_ID[idx]} ${y}`;
}

export function fmtDate(isoDate: string): string {
  const d = new Date(isoDate + "T00:00:00");
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

export function fmtConcentration(value: number | string | null, unit: string | null): string {
  if (value === null) return "—";
  if (typeof value === "string") return value;
  if (Math.abs(value) >= 1_000_000) {
    const exp = Math.floor(Math.log10(value));
    const mant = value / Math.pow(10, exp);
    return `${NF_DEC.format(mant)} × 10${toSuperscript(exp)} ${unit ?? ""}`.trim();
  }
  return `${NF_DEC.format(value)}${unit ? " " + unit : ""}`;
}

function toSuperscript(n: number): string {
  const map: Record<string, string> = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻",
  };
  return String(n).split("").map((c) => map[c] ?? c).join("");
}

export function thresholdLabel(t: {
  type: string;
  max?: number; min?: number; max_dev?: number; expected?: string; reference?: string;
} | null): string {
  if (!t) return "—";
  switch (t.type) {
    case "max": return `≤ ${fmtNum(t.max ?? null)}`;
    case "min": return `≥ ${fmtNum(t.min ?? null)}`;
    case "range": return `${fmtNum(t.min ?? null)} – ${fmtNum(t.max ?? null)}`;
    case "deviation": return `dev ±${fmtNum(t.max_dev ?? null)}${t.reference ? ` (${t.reference})` : ""}`;
    case "qualitative": return t.expected ?? "kualitatif";
    default: return "—";
  }
}
