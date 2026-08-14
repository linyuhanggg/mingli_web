/**
 * One-shot phase-1 reskin audit (2026-08-14).
 * - 8 routes x 4 viewports against http://127.0.0.1:3000 (system Chrome)
 * - asserts no horizontal overflow (scrollWidth <= innerWidth + 1)
 * - flags zero-area elements that carry their own text
 * - crawls computed font-sizes of visible text nodes against the frozen ladder
 *   {12,13,14,16,18,20,24,30} + hero band [40,64]; exempts --font-domain
 *   (Songti) chart glyphs and ui-monospace small text
 * - screenshots -> web/e2e/screenshots/audit-2026-08-14/phase1/{viewport}/{route}.png
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "http://127.0.0.1:3000";
const ROUTES = [
  ["/", "home"],
  ["/pricing", "pricing"],
  ["/about", "about"],
  ["/auth/login", "auth-login"],
  ["/daily", "daily"],
  ["/tools", "tools"],
  ["/bazi", "bazi"],
  ["/_ui-lab", "ui-lab"],
];
const VIEWPORTS = [360, 768, 1024, 1440];
const LADDER = [12, 13, 14, 16, 18, 20, 24, 30];
const outRoot = path.join(ROOT, "e2e", "screenshots", "audit-2026-08-14", "phase1");

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});

const layoutResults = [];
const fontOffenders = new Map();

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({
    viewport: { width: vp, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();
  for (const [route, name] of ROUTES) {
    const entry = { viewport: vp, route };
    try {
      const resp = await page.goto(BASE + route, {
        waitUntil: "networkidle",
        timeout: 45000,
      });
      entry.httpStatus = resp ? resp.status() : null;
      await page.waitForTimeout(250);

      const metrics = await page.evaluate((ladder) => {
        const ladderSet = new Set(ladder);
        const docEl = document.documentElement;
        const zero = [];
        const fonts = [];
        const walker = document.createTreeWalker(
          document.body,
          NodeFilter.SHOW_ELEMENT,
        );
        let n;
        while ((n = walker.nextNode())) {
          if (n.tagName === "OPTION") continue;
          if (typeof n.checkVisibility === "function" &&
              !n.checkVisibility({ checkVisibilityCSS: true })) continue;
          const cs = getComputedStyle(n);
          if (cs.display === "none" || cs.visibility === "hidden") continue;
          const ownText = [...n.childNodes].some(
            (c) => c.nodeType === 3 && c.textContent.trim().length > 0,
          );
          if (!ownText) continue;
          const r = n.getBoundingClientRect();
          if (r.width < 1 || r.height < 1) {
            zero.push({
              sel: `${n.tagName.toLowerCase()}.${String(n.className).slice(0, 60)}`,
              box: `${r.width.toFixed(1)}x${r.height.toFixed(1)}`,
              text: n.textContent.trim().slice(0, 20),
            });
          }
          const size = Math.round(parseFloat(cs.fontSize) * 100) / 100;
          const family = cs.fontFamily;
          const exempt =
            /Songti|STSong|Serif SC|ui-serif|serif/i.test(family) ||
            /ui-monospace|SFMono|Menlo|Consolas|monospace/i.test(family);
          const inHeroBand = size >= 40 && size <= 64;
          if (!exempt && !inHeroBand && !ladderSet.has(size)) {
            fonts.push({
              size,
              sel: `${n.tagName.toLowerCase()}.${String(n.className).slice(0, 60)}`,
              family: family.slice(0, 40),
              text: n.textContent.trim().slice(0, 20),
            });
          }
        }
        return {
          scrollWidth: docEl.scrollWidth,
          innerWidth: window.innerWidth,
          zero,
          fonts,
        };
      }, LADDER);

      entry.scrollWidth = metrics.scrollWidth;
      entry.innerWidth = metrics.innerWidth;
      entry.overflow = metrics.scrollWidth - metrics.innerWidth;
      entry.ok = entry.overflow <= 1 && metrics.zero.length === 0;
      entry.zero = metrics.zero.slice(0, 8);
      entry.zeroCount = metrics.zero.length;
      for (const f of metrics.fonts) {
        const key = `${f.size}px|${f.sel}|${route}`;
        if (!fontOffenders.has(key)) {
          fontOffenders.set(key, { ...f, viewport: vp, route });
        }
      }

      const dir = path.join(outRoot, String(vp));
      fs.mkdirSync(dir, { recursive: true });
      await page.screenshot({ path: path.join(dir, `${name}.png`) });
    } catch (err) {
      entry.error = String(err).slice(0, 300);
      entry.ok = false;
    }
    layoutResults.push(entry);
  }
  await ctx.close();
}

await browser.close();

const failures = layoutResults.filter((r) => !r.ok);
const report = {
  generatedAt: new Date().toISOString(),
  total: layoutResults.length,
  failures: failures.length,
  failureDetails: failures,
  fontOffenderCount: fontOffenders.size,
  fontOffenders: [...fontOffenders.values()],
};
fs.mkdirSync(outRoot, { recursive: true });
fs.writeFileSync(path.join(outRoot, "report.json"), JSON.stringify(report, null, 2));

console.log(`layout checks: ${layoutResults.length - failures.length}/${layoutResults.length} ok`);
for (const f of failures) {
  console.log(
    `FAIL ${f.viewport}px ${f.route} overflow=${f.overflow ?? "?"} zero=${f.zeroCount ?? "?"} ${f.error ?? ""}`,
  );
  for (const z of f.zero ?? []) console.log(`   zero-box ${z.box} ${z.sel} "${z.text}"`);
}
console.log(`font offenders (non-ladder, non-exempt): ${fontOffenders.size}`);
for (const f of [...fontOffenders.values()].slice(0, 60)) {
  console.log(`   ${f.size}px @${f.viewport}px ${f.route} ${f.sel} "${f.text}" [${f.family}]`);
}
process.exit(failures.length > 0 ? 1 : 0);
