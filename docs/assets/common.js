// Shared helpers for all dashboard pages.
// Loaded as ES module: <script type="module" src="./assets/common.js"></script>

import {
  initAnimations,
  injectKpiSkeleton,
  parseDisplayNumber,
} from "./animations.js";

// Re-export so pages can import skeleton/animation helpers from common.js too.
export {
  initAnimations,
  injectKpiSkeleton,
  injectChartSkeleton,
  clearSkeleton,
  countUpEl,
  setupCountUp,
  setupScrollReveal,
  parseDisplayNumber,
} from "./animations.js";

// ─── Data loading ─────────────────────────────────────────────────────

const DATA_BASE = "./data";
const _cache = new Map();

export async function loadJson(relPath) {
  if (_cache.has(relPath)) return _cache.get(relPath);
  const url = `${DATA_BASE}/${relPath}`;
  // cache: 'no-cache' forces a conditional GET (If-None-Match / If-Modified-Since)
  // so users always see fresh data after we deploy new JSON, while still getting
  // fast 304 Not Modified responses when nothing changed.
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
  const json = await res.json();
  _cache.set(relPath, json);
  return json;
}

export const loadMeta = () => loadJson("meta.json");
export const loadDataset = (id) => loadJson(`${id}.json`);
export const loadShared = (name) => loadJson(`shared/${name}.json`);

// ─── Number / date formatting (id-ID) ─────────────────────────────────

const NF_INT = new Intl.NumberFormat("id-ID");
const NF_DEC = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const NF_PCT = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];
export const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export function fmtInt(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return NF_INT.format(Math.round(v));
}
export function fmtNum(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return NF_DEC.format(v);
}
export function fmtKg(v) {
  if (v == null) return "—";
  return Number.isInteger(v) ? `${NF_INT.format(v)} kg` : `${NF_DEC.format(v)} kg`;
}
export function fmtPct(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return `${NF_PCT.format(v)}%`;
}
export function fmtMonth(iso) {
  if (!iso || !iso.includes("-")) return iso ?? "—";
  const [y, m] = iso.split("-");
  const idx = parseInt(m, 10) - 1;
  return idx >= 0 && idx < 12 ? `${MONTHS_ID[idx]} ${y}` : iso;
}
export function fmtThreshold(t) {
  if (!t) return "—";
  switch (t.type) {
    case "max": return `≤ ${fmtNum(t.max)}`;
    case "min": return `≥ ${fmtNum(t.min)}`;
    case "range": return `${fmtNum(t.min)} – ${fmtNum(t.max)}`;
    case "deviation": return `dev ±${fmtNum(t.max_dev)}`;
    case "qualitative": return t.expected ?? "kualitatif";
    default: return "—";
  }
}

// ─── DOM helpers ──────────────────────────────────────────────────────

export function $(sel, root = document) { return root.querySelector(sel); }
export function $$(sel, root = document) { return [...root.querySelectorAll(sel)]; }
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

// ─── Layout (sidebar) ────────────────────────────────────────────────

const NAV = [
  { href: "./index.html", label: "Ringkasan", icon: "layout-dashboard" },
  { href: "./pengolahan-sampah.html", label: "Pengolahan Sampah", icon: "recycle" },
  { href: "./timbulan-sampah.html", label: "Timbulan Sampah", icon: "trash-2" },
  { href: "./kualitas-air.html", label: "Kualitas Air", icon: "droplet" },
  { href: "./insiden-vegetasi.html", label: "Insiden Vegetasi", icon: "trees" },
  { href: "./kecelakaan-lalu-lintas.html", label: "Kecelakaan Lalu Lintas", icon: "car-front" },
  { href: "./limbah-b3.html", label: "Limbah B3", icon: "flask" },
  { href: "./listrik.html", label: "Listrik", icon: "zap" },
];

// Minimal inline SVG icons (avoiding external lib for offline + speed)
const ICONS = {
  "layout-dashboard": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>`,
  "recycle": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 19H4.815a1.83 1.83 0 0 1-1.57-.881 1.785 1.785 0 0 1-.004-1.784L7.196 9.5"/><path d="M11 19h8.203a1.83 1.83 0 0 0 1.556-.89 1.784 1.784 0 0 0 0-1.775l-1.226-2.12"/><path d="m14 16-3 3 3 3"/><path d="M8.293 13.596 7.196 9.5 3.1 10.598"/><path d="m9.344 5.811 1.093-1.892A1.83 1.83 0 0 1 12.001 3a1.83 1.83 0 0 1 1.564.92l3.943 6.83"/><path d="m13.378 9.633 4.096 1.098 1.097-4.096"/></svg>`,
  "trash-2": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>`,
  "droplet": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/></svg>`,
  "trees": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 10v.2A3 3 0 0 1 8.9 16v0H5v0h0a3 3 0 0 1-1-5.8V10a3 3 0 0 1 6 0Z"/><path d="M7 16v6"/><path d="M13 19h6"/><path d="M16 19v3"/><path d="M16 12a3 3 0 0 0 3-3 3 3 0 0 0-.92-2.16A3 3 0 0 0 16 3a3 3 0 0 0-2.08 5.84A3 3 0 0 0 13 11a3 3 0 0 0 3 3v0Z"/></svg>`,
  "car-front": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8"/><path d="M7 14h.01"/><path d="M17 14h.01"/><rect width="18" height="8" x="3" y="10" rx="2"/><path d="M5 18v2"/><path d="M19 18v2"/></svg>`,
  "info": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
  "menu": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>`,
  "flask": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v6.5L2 21a1 1 0 0 0 .9 1.5h18.2A1 1 0 0 0 22 21L15 8.5V2"/><path d="M8 2h8"/><path d="M7.5 14h9"/></svg>`,
  "zap": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>`,
};

export function renderSidebar(currentPage) {
  const sidebar = $("#sidebar");
  if (!sidebar) return;
  sidebar.innerHTML = `
    <a href="./index.html" class="sidebar-brand" style="text-decoration: none;">
      <div class="logo-row">
        <img class="logo-img logo-unpad" src="./assets/logo-unpad.webp" alt="UNPAD" />
        <img class="logo-img logo-pkbkkl" src="./assets/logo-pkbkkl.png" alt="PKBKKL"
          onerror="this.onerror=null; this.src='./assets/logo-pkbkkl.svg'" />
      </div>
      <div class="brand-text">
        <span class="org-mark">UNIVERSITAS PADJADJARAN</span>
        <span class="product-name">Dashboard Pemantauan Lingkungan</span>
      </div>
    </a>
    <nav class="px-3 py-4 space-y-1">
      ${NAV.map((n) => `
        <a href="${n.href}" class="nav-link${currentPage === n.href.replace("./", "") ? " active" : ""}">
          <span class="w-4 h-4 inline-flex">${ICONS[n.icon] ?? ""}</span>
          <span>${n.label}</span>
        </a>
      `).join("")}
    </nav>
    <div class="sidebar-footer">
      <div class="green-campus">Green Campus UNPAD</div>
      <div>Universitas Padjadjaran · Jatinangor</div>
    </div>
  `;
}

export function renderHeader({ title, period, description }) {
  const header = $("#page-header");
  if (!header) return;
  header.classList.add("reveal");
  header.style.setProperty("--reveal-delay", "0ms");
  header.innerHTML = `
    <div class="flex flex-wrap items-baseline gap-3">
      <h1 class="text-2xl font-semibold">${title}</h1>
      ${period ? `<span class="text-sm period-pill rounded-full px-3 py-1">${period}</span>` : ""}
    </div>
    ${description ? `<p class="mt-2 text-slate-600 leading-relaxed max-w-3xl">${description}</p>` : ""}
  `;
  initAnimations(header.parentElement || document);
}

// ─── KPI cards ────────────────────────────────────────────────────────

export function renderKpis(containerSel, cards) {
  const container = $(containerSel);
  if (!container) return;
  const accentMap = {
    brand: "bg-green-50 text-green-700",
    blue: "bg-blue-50 text-blue-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
    slate: "bg-slate-100 text-slate-700",
  };
  container.classList.add("reveal");
  container.innerHTML = cards
    .map((c, i) => {
      const accent = accentMap[c.accent ?? "brand"];
      // Build animated value: extract leading id-ID number + any trailing
      // suffix ("%", " kg", " L", etc.) so the number animates while the
      // suffix stays put. Falls back to static text when no leading number.
      let rawValue = c.rawValue;
      let suffix = "";
      let decimals = c.decimals;
      if (rawValue == null && typeof c.value === "string") {
        const m = c.value.trim().match(/^(-?\d[\d.,]*)(.*)$/);
        if (m) {
          rawValue = parseDisplayNumber(m[1]);
          suffix = m[2] || "";
          if (decimals == null) {
            // Infer decimals from the id-ID decimal separator (",")
            decimals = m[1].includes(",")
              ? m[1].split(",")[1].length
              : 0;
          }
        }
      }
      let valueHtml;
      if (rawValue != null && Number.isFinite(rawValue)) {
        const safeSuffix = suffix.replace(/"/g, "&quot;");
        valueHtml = `<span data-countup="${rawValue}" data-countup-decimals="${decimals ?? 0}" data-countup-suffix="${safeSuffix}">${c.value}</span>`;
      } else {
        valueHtml = String(c.value);
      }
      const inner = `
        <div class="card card-stagger p-5 h-full flex flex-col" style="--i:${i}">
          <div class="flex items-start justify-between">
            <div class="text-xs font-medium uppercase tracking-wide text-slate-400">${c.label}</div>
            ${c.icon ? `<div class="rounded-lg p-2 ${accent}"><span class="w-4 h-4 inline-flex">${ICONS[c.icon] ?? ""}</span></div>` : ""}
          </div>
          <div class="mt-3 flex items-baseline gap-1.5">
            <div class="text-2xl font-semibold text-slate-900 tabular-nums">${valueHtml}</div>
            ${c.unit ? `<div class="text-sm text-slate-400">${c.unit}</div>` : ""}
          </div>
          ${c.trend ? `<div class="mt-2 text-xs text-slate-600">${c.trend}</div>` : ""}
        </div>`;
      return c.href ? `<a href="${c.href}" class="block">${inner}</a>` : inner;
    })
    .join("");
  initAnimations(container.parentElement || document);
}

// ─── Data quality flags ───────────────────────────────────────────────

export function renderFlags(flags, containerSel = "#flags", title = "Catatan Integritas Data") {
  const container = $(containerSel);
  if (!container || !flags?.length) return;
  const stylesBySeverity = {
    info: "bg-blue-50 border-blue-200 text-blue-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
    error: "bg-red-50 border-red-200 text-red-800",
  };
  const labels = { info: "Info", warning: "Peringatan", error: "Error" };
  container.innerHTML = `
    <h2 class="text-sm font-semibold text-slate-700 mb-3">${title}</h2>
    <ul class="space-y-2">
      ${flags.map((f) => `
        <li class="rounded-lg border px-3 py-2.5 text-sm ${stylesBySeverity[f.severity] ?? ""}">
          <span class="font-medium mr-1.5">${labels[f.severity] ?? f.severity}.</span>${f.message}
        </li>
      `).join("")}
    </ul>
  `;
}

// ─── Footer ───────────────────────────────────────────────────────────

export function renderFooter(meta) {
  const footer = $("#page-footer");
  if (!footer) return;
  footer.innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span><span class="leaf-mark"></span>${meta.dashboard.organization} · ${meta.dashboard.subtitle}</span>
      <span>v${meta.dashboard.version} · diperbarui ${meta.dashboard.last_updated}</span>
    </div>
  `;
}

// ─── Page bootstrap (called by each page) ────────────────────────────

export async function bootstrap(currentPage) {
  // Inject skeleton placeholders BEFORE awaiting data so users see motion immediately.
  const kpisEl = $("#kpis");
  if (kpisEl && !kpisEl.children.length) {
    // Match the grid columns used across pages (~3 on lg, 2 on sm)
    injectKpiSkeleton(kpisEl, 6);
  }

  const meta = await loadMeta();
  document.title = `${document.title.split(" · ")[0]} · Dashboard Pemantauan Lingkungan UNPAD`;
  renderSidebar(currentPage);
  renderFooter(meta);
  setupMobileSidebar();

  // Apply a gentle stagger to the first few sections on the page; CSS
  // already hides every <main> > <section> by default until reveal-visible
  // is added by the IntersectionObserver in initAnimations().
  document.querySelectorAll("main > section").forEach((section, i) => {
    if (section.classList.contains("no-reveal")) return;
    if (i < 4 && !section.style.getPropertyValue("--reveal-delay")) {
      section.style.setProperty("--reveal-delay", `${i * 70}ms`);
    }
  });

  // Kick off observers; will re-run idempotently after each render*() call.
  initAnimations(document);
  return meta;
}

// ─── Mobile sidebar toggle ───────────────────────────────────────────

function setupMobileSidebar() {
  const sidebar = $("#sidebar");
  const trigger = $("#sidebar-toggle");
  if (!sidebar || !trigger) return;

  // Standardize hamburger icon (replace any inline text/svg in HTML files)
  trigger.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/></svg>`;
  trigger.setAttribute("aria-label", "Toggle menu");
  trigger.setAttribute("aria-expanded", "false");

  // Inject backdrop (1 per dokumen)
  let backdrop = document.querySelector(".sidebar-backdrop");
  if (!backdrop) {
    backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    document.body.appendChild(backdrop);
  }

  const isMobile = () => window.matchMedia("(max-width: 1023px)").matches;
  const open = () => {
    sidebar.classList.add("open");
    document.body.classList.add("sidebar-open");
    trigger.setAttribute("aria-expanded", "true");
  };
  const close = () => {
    sidebar.classList.remove("open");
    document.body.classList.remove("sidebar-open");
    trigger.setAttribute("aria-expanded", "false");
  };

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    sidebar.classList.contains("open") ? close() : open();
  });
  backdrop.addEventListener("click", close);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("open")) close();
  });
  // Tutup sidebar otomatis saat user klik nav-link di mobile
  sidebar.querySelectorAll(".nav-link, .sidebar-brand").forEach((link) => {
    link.addEventListener("click", () => {
      if (isMobile()) setTimeout(close, 80);
    });
  });
  // Auto-close kalau resize ke desktop saat sidebar terbuka
  window.addEventListener("resize", () => {
    if (!isMobile() && sidebar.classList.contains("open")) close();
  });
}

