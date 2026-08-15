// Objective visual-audit metrics: overflow, palette, type scale, tap targets, contrast.
import { chromium } from "@playwright/test";

const base = process.argv[2] ?? "http://127.0.0.1:3000";
const routes = ["/", "/bazi", "/pricing", "/about", "/auth/login", "/_ui-lab", "/daily", "/tools"];
const viewports = [[360, 800], [768, 1024], [1024, 768], [1440, 900]];

const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" });

function luminance(r, g, b) {
  const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
function parseColor(s) {
  const m = s.match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const [r, g, b, a] = m[1].split(",").map((x) => parseFloat(x));
  return { r, g, b, a: a === undefined || Number.isNaN(a) ? 1 : a };
}
function contrast(fg, bg) {
  const L1 = luminance(fg.r, fg.g, fg.b), L2 = luminance(bg.r, bg.g, bg.b);
  const [hi, lo] = L1 > L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}

for (const [w, h] of viewports) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  for (const route of routes) {
    try {
      await page.goto(base + route, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(300);
      const data = await page.evaluate(() => {
        const doc = document.documentElement;
        const overflowX = doc.scrollWidth > window.innerWidth + 1;
        const colors = new Set(), fonts = new Set(), sizes = new Set();
        const smallTargets = [];
        const texts = [];
        document.querySelectorAll("*").forEach((el) => {
          const cs = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) return;
          colors.add(cs.color); colors.add(cs.backgroundColor);
          fonts.add(cs.fontFamily.split(",")[0]);
          sizes.add(Math.round(parseFloat(cs.fontSize)));
          const interactive = el.closest("a,button,[role=button],input,select,textarea,[tabindex]");
          if (interactive === el || (interactive && el === interactive)) {
            if ((rect.width < 44 || rect.height < 44) && rect.width > 0) {
              const label = (el.textContent || "").trim().slice(0, 24);
              if (label) smallTargets.push(`${el.tagName.toLowerCase()} ${Math.round(rect.width)}x${Math.round(rect.height)} "${label}"`);
            }
          }
          if (el.children.length === 0 && el.textContent && el.textContent.trim().length > 1) {
            texts.push({ color: cs.color, bg: cs.backgroundColor, size: parseFloat(cs.fontSize), text: el.textContent.trim().slice(0, 18) });
          }
        });
        return { overflowX, scrollW: doc.scrollWidth, innerW: window.innerWidth,
          colors: [...colors].slice(0, 40), fonts: [...fonts], sizes: [...sizes].sort((a, b) => a - b),
          smallTargets: smallTargets.slice(0, 12), texts: texts.slice(0, 400) };
      });
      // contrast check on leaf text nodes
      const bad = [];
      for (const t of data.texts) {
        const fg = parseColor(t.color), bg = parseColor(t.bg);
        if (!fg || !bg || bg.a < 0.95) continue; // skip transparent bg (unknown stacking)
        const ratio = contrast(fg, bg);
        const min = t.size >= 18 ? 3 : 4.5;
        if (ratio < min) bad.push(`${ratio.toFixed(2)} ${Math.round(t.size)}px "${t.text}"`);
      }
      console.log(JSON.stringify({ vp: w, route, overflowX: data.overflowX, scrollW: data.scrollW,
        fontCount: data.fonts.length, fonts: data.fonts, sizes: data.sizes,
        smallTargets: data.smallTargets, contrastFails: bad.slice(0, 10), contrastFailCount: bad.length }));
    } catch (err) {
      console.log(JSON.stringify({ vp: w, route, error: String(err).slice(0, 120) }));
    }
  }
  await page.close();
}
await browser.close();
