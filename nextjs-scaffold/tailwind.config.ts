import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef9f1",
          100: "#d4f0db",
          500: "#16a34a",
          600: "#15803d",
          700: "#166534",
          900: "#14532d",
        },
        ink: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          400: "#94a3b8",
          600: "#475569",
          700: "#334155",
          900: "#0f172a",
        },
        category: {
          organik: "#16a34a",
          anorganik: "#2563eb",
          residu: "#737373",
          kompos: "#65a30d",
          rdf: "#0891b2",
          maggot: "#eab308",
          dumping: "#ef4444",
          compliant: "#16a34a",
          exceedance: "#dc2626",
          below: "#94a3b8",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
