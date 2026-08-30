// Generates the presentation's abstract vector art (no diffusion model available):
//   assets/images/cover-hero.svg     — node-network hero for Frame 1
//   assets/images/section-texture.svg — faint contour texture for text frames
//   assets/images/close-bg.svg       — calmer network fading right, for Frame 19
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const DIR = join(dirname(fileURLToPath(import.meta.url)), "assets", "images");
mkdirSync(DIR, { recursive: true });

const W = 1920;
const H = 1080;

// Small deterministic PRNG (mulberry32).
function rng(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const INK = "#131310";
const SLATE = "#5b76ad";
const SLATE_DIM = "#39415e";
const AMBER = "#d99a2b";

function network({ seed, count, calmerRight = false, edgeBias = true, neighbors = 2, maxDist = 260 }) {
  const r = rng(seed);
  const pts = [];
  for (let i = 0; i < count; i++) {
    let x = r() * W;
    let y = r() * H;
    // Bias points toward the edges so the middle stays quiet for text.
    if (edgeBias) {
      const cx = (x - W / 2) / (W / 2);
      const cy = (y - H / 2) / (H / 2);
      const d = Math.sqrt(cx * cx + cy * cy);
      if (d < 0.55 && r() > 0.25) {
        x = r() * W;
        y = r() * H;
      }
    }
    if (calmerRight && x > W * 0.58 && r() > 0.35) continue;
    pts.push({ x, y, amber: r() < 0.08 });
  }
  // Edges: connect each point to its 2 nearest neighbours.
  const lines = [];
  for (let i = 0; i < pts.length; i++) {
    const d = pts
      .map((p, j) => ({ j, dist: Math.hypot(p.x - pts[i].x, p.y - pts[i].y) }))
      .filter((o) => o.j !== i)
      .sort((a, b) => a.dist - b.dist)
      .slice(0, neighbors);
    for (const { j, dist } of d) {
      if (dist < maxDist && i < j) lines.push({ a: pts[i], b: pts[j] });
    }
  }
  return { pts, lines };
}

function heroSvg() {
  const { pts, lines } = network({ seed: 42, count: 175, neighbors: 3, maxDist: 300 });
  const grid = [];
  for (let x = 0; x <= W; x += 80)
    grid.push(`<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke="#ffffff" stroke-opacity="0.02"/>`);
  for (let y = 0; y <= H; y += 80)
    grid.push(`<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="#ffffff" stroke-opacity="0.02"/>`);
  const edgeEls = lines
    .map(
      (l) =>
        `<line x1="${l.a.x.toFixed(1)}" y1="${l.a.y.toFixed(1)}" x2="${l.b.x.toFixed(1)}" y2="${l.b.y.toFixed(
          1,
        )}" stroke="${SLATE_DIM}" stroke-width="1" stroke-opacity="0.62"/>`,
    )
    .join("");
  const nodeEls = pts
    .map((p) => {
      const col = p.amber ? AMBER : SLATE;
      const rad = p.amber ? 5 : 3;
      const glow = p.amber
        ? `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="12" fill="${AMBER}" fill-opacity="0.12"/>`
        : "";
      return `${glow}<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${rad}" fill="${col}" fill-opacity="${
        p.amber ? 0.95 : 0.9
      }"/>`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs>
<radialGradient id="bg" cx="50%" cy="42%" r="75%">
<stop offset="0%" stop-color="#1b1b16"/>
<stop offset="60%" stop-color="${INK}"/>
<stop offset="100%" stop-color="#0d0d0b"/>
</radialGradient>
<radialGradient id="quiet" cx="50%" cy="46%" r="44%">
<stop offset="0%" stop-color="${INK}" stop-opacity="0.6"/>
<stop offset="100%" stop-color="${INK}" stop-opacity="0"/>
</radialGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bg)"/>
<g>${grid.join("")}</g>
<g>${edgeEls}</g>
<g>${nodeEls}</g>
<rect width="${W}" height="${H}" fill="url(#quiet)"/>
<rect width="${W}" height="${H}" fill="none" stroke="#ffffff" stroke-opacity="0.04" stroke-width="2"/>
</svg>`;
}

function textureSvg() {
  const r = rng(7);
  const paths = [];
  for (let k = 0; k < 22; k++) {
    const baseY = 40 + k * 46 + r() * 12;
    let d = `M -20 ${baseY.toFixed(1)}`;
    for (let x = 0; x <= W + 40; x += 60) {
      const y = baseY + Math.sin((x + k * 120) / 180) * (10 + k * 0.6) + r() * 4;
      d += ` L ${x} ${y.toFixed(1)}`;
    }
    paths.push(`<path d="${d}" fill="none" stroke="#7a7568" stroke-opacity="0.10" stroke-width="1"/>`);
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="#faf9f6"/>
<g>${paths.join("")}</g>
</svg>`;
}

function closeSvg() {
  const { pts, lines } = network({ seed: 99, count: 90, calmerRight: true, edgeBias: false });
  const edgeEls = lines
    .map(
      (l) =>
        `<line x1="${l.a.x.toFixed(1)}" y1="${l.a.y.toFixed(1)}" x2="${l.b.x.toFixed(1)}" y2="${l.b.y.toFixed(
          1,
        )}" stroke="${SLATE_DIM}" stroke-width="1" stroke-opacity="0.45"/>`,
    )
    .join("");
  const nodeEls = pts
    .map(
      (p) =>
        `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${p.amber ? 4 : 2.4}" fill="${
          p.amber ? AMBER : SLATE
        }" fill-opacity="0.75"/>`,
    )
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
<stop offset="0%" stop-color="${INK}" stop-opacity="0"/>
<stop offset="55%" stop-color="${INK}" stop-opacity="0.35"/>
<stop offset="100%" stop-color="${INK}" stop-opacity="0.9"/>
</linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="${INK}"/>
<g>${edgeEls}</g>
<g>${nodeEls}</g>
<rect width="${W}" height="${H}" fill="url(#fade)"/>
</svg>`;
}

writeFileSync(join(DIR, "cover-hero.svg"), heroSvg());
writeFileSync(join(DIR, "section-texture.svg"), textureSvg());
writeFileSync(join(DIR, "close-bg.svg"), closeSvg());
console.log("wrote cover-hero.svg, section-texture.svg, close-bg.svg to", DIR);
