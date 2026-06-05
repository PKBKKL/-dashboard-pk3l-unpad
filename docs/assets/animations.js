// Lightweight, dependency-free animation utilities for the dashboard.
// - countUp: animate numeric KPI values
// - scrollReveal: fade-in sections as they enter the viewport
// - skeleton helpers: shimmer placeholders during data loading
// Respects prefers-reduced-motion automatically.

const PREFERS_REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const COUNT_DURATION_DEFAULT = 1200;

const NF_CACHE = {};
function getNF(decimals) {
  const key = String(decimals);
  if (!NF_CACHE[key]) {
    NF_CACHE[key] = new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  return NF_CACHE[key];
}

// Parse an id-ID formatted display number back to a Number.
// "359.932" → 359932 ; "5.900,52" → 5900.52 ; "0,5%" → 0.5
export function parseDisplayNumber(str) {
  if (str == null) return null;
  const cleaned = String(str).replace(/[^\d,.\-]/g, "");
  if (!cleaned) return null;
  let n;
  if (cleaned.includes(".") && cleaned.includes(",")) {
    n = parseFloat(cleaned.replace(/\./g, "").replace(",", "."));
  } else if (cleaned.includes(",")) {
    n = parseFloat(cleaned.replace(",", "."));
  } else if (cleaned.includes(".")) {
    // Heuristic: "." with exactly 3 digits after = thousands separator (id-ID).
    // Otherwise treat as decimal (rare in our pipeline).
    if (/^-?\d{1,3}(\.\d{3})+$/.test(cleaned)) {
      n = parseFloat(cleaned.replace(/\./g, ""));
    } else {
      n = parseFloat(cleaned);
    }
  } else {
    n = parseFloat(cleaned);
  }
  return Number.isFinite(n) ? n : null;
}

export function countUpEl(el) {
  if (!el || el.dataset.countupDone === "1") return;
  const target = parseFloat(el.dataset.countup);
  if (!Number.isFinite(target)) return;
  el.dataset.countupDone = "1";
  const decimals = parseInt(el.dataset.countupDecimals || "0", 10);
  const duration = parseInt(
    el.dataset.countupDuration || String(COUNT_DURATION_DEFAULT),
    10,
  );
  const prefix = el.dataset.countupPrefix || "";
  const suffix = el.dataset.countupSuffix || "";
  const nf = getNF(decimals);
  const fmt = (v) => prefix + nf.format(v) + suffix;

  if (PREFERS_REDUCED || duration <= 0) {
    el.textContent = fmt(target);
    return;
  }
  const start = performance.now();
  function frame(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
    el.textContent = fmt(target * eased);
    if (t < 1) requestAnimationFrame(frame);
    else el.textContent = fmt(target);
  }
  requestAnimationFrame(frame);
}

export function setupCountUp(root = document) {
  root
    .querySelectorAll("[data-countup]:not([data-countup-done])")
    .forEach(countUpEl);
}

// IntersectionObserver-based fade-in for .reveal elements AND every
// <main> > <section> (default-hidden by CSS until JS reveals them).
// Also fires count-up for [data-countup] children inside revealed sections.
export function setupScrollReveal(root = document) {
  const selector =
    "main > section:not(.no-reveal):not(.reveal-visible), .reveal:not(.reveal-visible)";
  const elements = root.querySelectorAll(selector);
  if (!elements.length) return;

  if (PREFERS_REDUCED || typeof IntersectionObserver === "undefined") {
    elements.forEach((el) => el.classList.add("reveal-visible"));
    setupCountUp(root);
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("reveal-visible");
          // Animate any numeric counters that came into view
          const counters = entry.target.querySelectorAll
            ? entry.target.querySelectorAll(
                "[data-countup]:not([data-countup-done])",
              )
            : [];
          counters.forEach((c) => {
            // Slight stagger so number animation feels tied to the reveal
            setTimeout(() => countUpEl(c), 180);
          });
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.05, rootMargin: "0px 0px -40px 0px" },
  );
  elements.forEach((el) => observer.observe(el));
}

// Drop in shimmer placeholders into a KPI grid before real data lands.
export function injectKpiSkeleton(target, count = 6) {
  const el = typeof target === "string" ? document.querySelector(target) : target;
  if (!el || el.children.length) return;
  el.innerHTML = Array.from(
    { length: count },
    () => `<div class="skeleton-card" aria-hidden="true"></div>`,
  ).join("");
}

// Drop in shimmer placeholder for a chart container.
export function injectChartSkeleton(target, height = 320) {
  const el = typeof target === "string" ? document.querySelector(target) : target;
  if (!el || el.children.length) return;
  el.style.minHeight = `${height}px`;
  el.innerHTML = `<div class="skeleton-chart" style="height:${height}px" aria-hidden="true"></div>`;
}

export function clearSkeleton(target) {
  const el = typeof target === "string" ? document.querySelector(target) : target;
  if (!el) return;
  el
    .querySelectorAll(".skeleton-card, .skeleton-line, .skeleton-chart")
    .forEach((s) => s.remove());
}

// Public entry: call once after content is in the DOM. Idempotent.
export function initAnimations(root = document) {
  setupScrollReveal(root);
  // Fallback: count-up anything that's above the fold OR not inside a .reveal
  // (the observer would otherwise wait indefinitely).
  setTimeout(() => setupCountUp(root), 60);
}
