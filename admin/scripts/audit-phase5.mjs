/**
 * One-shot phase-5 browser audit (Admin token/layout alignment, 2026-08-15).
 *
 * The API service is not required for this audit. Normal Admin routes render
 * their honest unavailable/error states when the local API is absent; the
 * browser audit checks the shell, responsive contract, controls, and route
 * boundaries around those states.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "http://127.0.0.1:3001";
const VIEWPORTS = [360, 768, 1024, 1440];
const ROUTES = [
  ["/", "root"],
  ["/login", "login"],
  ["/dashboard", "dashboard"],
  ["/users", "users"],
  ["/users/demo-user", "users-detail"],
  ["/subjects", "subjects"],
  ["/subjects/demo-subject", "subjects-detail"],
  ["/data-rights", "data-rights"],
  ["/support-cases", "support-cases"],
  ["/products", "products"],
  ["/products/demo-product/versions", "product-versions"],
  ["/capabilities", "capabilities"],
  ["/cms/pages", "cms-pages"],
  ["/cms/daily", "cms-daily"],
  ["/cms/tools", "cms-tools"],
  ["/cms/library", "cms-library"],
  ["/cms/help", "cms-help"],
  ["/cms/policies", "cms-policies"],
  ["/charts", "charts"],
  ["/readings", "readings"],
  ["/readings/demo-reading", "reading-detail"],
  ["/reading-jobs", "reading-jobs"],
  ["/verifications", "verifications"],
  ["/observations", "observations"],
  ["/runtime", "runtime"],
  ["/model-profiles", "model-profiles"],
  ["/orders", "orders"],
  ["/payments", "payments"],
  ["/refunds", "refunds"],
  ["/reconciliation", "reconciliation"],
  ["/entitlements", "entitlements"],
  ["/referrals", "referrals"],
  ["/referrals/demo-referral", "referral-detail"],
  ["/appeals", "appeals"],
  ["/staff", "staff"],
  ["/sessions", "sessions"],
  ["/notifications", "notifications"],
  ["/audit", "audit"],
  ["/settings", "settings"],
  ["/health", "health"],
  ["/_ui-lab", "ui-lab"],
];
const SCREENSHOT_ROUTES = new Set([
  "login",
  "dashboard",
  "users",
  "readings",
  "runtime",
  "orders",
  "settings",
  "health",
  "ui-lab",
]);
const OUT_ROOT = path.join(ROOT, "e2e", "screenshots", "audit-2026-08-14", "phase5");

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

function addFailure(entry, check, reason) {
  entry.failures.push({ check, reason });
}

async function pageMetrics(page) {
  return page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0;
    };
    const rect = (selector) => {
      const element = document.querySelector(selector);
      if (!element || !visible(element)) return null;
      const box = element.getBoundingClientRect();
      return {
        display: getComputedStyle(element).display,
        width: Math.round(box.width * 100) / 100,
        height: Math.round(box.height * 100) / 100,
      };
    };
    const targetViolations = [...document.querySelectorAll(
      "button, select, textarea, input:not([type=checkbox]):not([type=radio]), nav[aria-label=\"运营导航\"] a, button[aria-label=\"打开运营导航\"]",
    )]
      .filter(visible)
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          text: element.textContent?.trim().slice(0, 60) ?? "",
          width: Math.round(box.width * 100) / 100,
          height: Math.round(box.height * 100) / 100,
        };
      })
      .filter(({ width, height }) => width < 44 || height < 44);
    const bodyText = document.body.innerText;
    const styles = [...document.querySelectorAll("style")]
      .map((style) => style.textContent ?? "")
      .join("\n");
    return {
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      mainCount: [...document.querySelectorAll("main")].filter(visible).length,
      h1Count: [...document.querySelectorAll("h1")].filter(visible).length,
      h1Text: [...document.querySelectorAll("h1")].filter(visible).map((heading) => heading.textContent?.trim() ?? ""),
      top: rect("header"),
      desktopNavigation: rect('nav[aria-label="运营导航"]'),
      mobileMenu: rect('button[aria-label="打开运营导航"]'),
      targetViolations,
      bodyText,
      hasGradient: /gradient\(/i.test(styles),
      hasGlassCopy: /backdrop-filter|glassmorphism|发光/i.test(styles + bodyText),
    };
  });
}

function assertShell(entry, metrics, route, viewport) {
  const isLogin = route === "/login";
  if (metrics.h1Count !== 1) {
    addFailure(entry, "h1-landmark", `expected one visible h1, found ${metrics.h1Count}`);
  }
  if (isLogin) {
    if (metrics.mainCount !== 0) {
      addFailure(entry, "login-shell", `login should not render AdminShell main, found ${metrics.mainCount}`);
    }
    return;
  }
  if (metrics.mainCount !== 1) {
    addFailure(entry, "main-landmark", `expected one visible main, found ${metrics.mainCount}`);
  }
  if (!metrics.top || metrics.top.height < 56 || metrics.top.height > 64) {
    addFailure(entry, "topbar-height", `expected 56–64px top bar, received ${JSON.stringify(metrics.top)}`);
  }
  if (viewport >= 1024) {
    if (!metrics.desktopNavigation || Math.abs(metrics.desktopNavigation.width - 240) > 1) {
      addFailure(entry, "desktop-sidebar", `expected 240px sidebar from 1024px, received ${JSON.stringify(metrics.desktopNavigation)}`);
    }
    if (metrics.mobileMenu) {
      addFailure(entry, "desktop-menu-boundary", "mobile menu remains visible at desktop breakpoint");
    }
  } else {
    if (metrics.desktopNavigation) {
      addFailure(entry, "mobile-sidebar-boundary", "desktop sidebar remains visible below 1024px");
    }
    if (!metrics.mobileMenu) {
      addFailure(entry, "mobile-menu", "mobile menu is not visible below 1024px");
    }
  }
}

async function run() {
  const results = [];
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
  });

  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: viewport, height: 900 },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();

      try {
        for (const [route, name] of ROUTES) {
          const entry = { viewport, route, name, failures: [] };
          const runtimeErrors = [];
          page.removeAllListeners("pageerror");
          page.on("pageerror", (error) => runtimeErrors.push(errorMessage(error)));

          try {
            const response = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 45000 });
            await page.waitForTimeout(250);
            entry.httpStatus = response ? response.status() : null;
            entry.finalPathname = new URL(page.url()).pathname;
            if (route === "/" ? entry.finalPathname !== "/dashboard" : entry.finalPathname !== route) {
              addFailure(entry, "final-url", `expected ${route === "/" ? "/dashboard" : route}, received ${entry.finalPathname}`);
            }

            const metrics = await pageMetrics(page);
            entry.metrics = {
              scrollWidth: metrics.scrollWidth,
              innerWidth: metrics.innerWidth,
              overflow: metrics.scrollWidth - metrics.innerWidth,
              mainCount: metrics.mainCount,
              h1Count: metrics.h1Count,
              h1Text: metrics.h1Text,
              top: metrics.top,
              desktopNavigation: metrics.desktopNavigation,
              mobileMenu: metrics.mobileMenu,
              targetViolations: metrics.targetViolations,
            };
            if (metrics.scrollWidth > metrics.innerWidth + 1) {
              addFailure(entry, "horizontal-overflow", `scrollWidth ${metrics.scrollWidth}px exceeds innerWidth ${metrics.innerWidth}px`);
            }
            assertShell(entry, metrics, route, viewport);
            if (metrics.targetViolations.length > 0) {
              addFailure(entry, "touch-targets", JSON.stringify(metrics.targetViolations));
            }
            if (metrics.hasGradient) {
              addFailure(entry, "gradient-boundary", "computed stylesheet contains gradient()");
            }
            if (metrics.hasGlassCopy) {
              addFailure(entry, "glass-boundary", "found glass/glow implementation or copy");
            }
            if (name === "ui-lab") {
              if (!metrics.bodyText.includes("UI 演示数据")) {
                addFailure(entry, "ui-lab-boundary", "expected explicit Admin UI Lab fixture label");
              }
              if (!metrics.bodyText.includes("演示控制台")) {
                addFailure(entry, "ui-lab-controls", "expected Admin UI Lab controls");
              }
            }
            if (route === "/login") {
              if ((await page.getByRole("form", { name: "员工登录" }).count()) !== 1) {
                addFailure(entry, "login-form", "expected one employee login form");
              }
            }
          } catch (error) {
            addFailure(entry, "route-audit", errorMessage(error));
          }

          if (runtimeErrors.length > 0) {
            entry.runtimeErrors = runtimeErrors;
            addFailure(entry, "runtime-errors", runtimeErrors.join(" | "));
          }

          if (SCREENSHOT_ROUTES.has(name)) {
            const screenshotPath = path.join(OUT_ROOT, String(viewport), `${name}.png`);
            try {
              fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
              await page.screenshot({ path: screenshotPath, fullPage: true });
              entry.screenshot = path.relative(ROOT, screenshotPath);
            } catch (error) {
              addFailure(entry, "screenshot", errorMessage(error));
            }
          }

          entry.ok = entry.failures.length === 0;
          results.push(entry);
        }
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  const failures = results.filter((entry) => !entry.ok);
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE,
    routeCount: ROUTES.length,
    viewportCount: VIEWPORTS.length,
    screenshotRouteCount: SCREENSHOT_ROUTES.size,
    total: results.length,
    passed: results.length - failures.length,
    failed: failures.length,
    results,
  };
  fs.mkdirSync(OUT_ROOT, { recursive: true });
  fs.writeFileSync(path.join(OUT_ROOT, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  console.log(`phase-5 Admin audit: ${report.passed}/${report.total} route/viewport combinations passed`);
  for (const entry of failures) {
    for (const failure of entry.failures) {
      console.log(`FAIL ${entry.viewport}px ${entry.route} [${failure.check}] ${failure.reason}`);
    }
  }
  process.exitCode = failures.length > 0 ? 1 : 0;
}

run().catch((error) => {
  console.log(JSON.stringify({ generatedAt: new Date().toISOString(), baseUrl: BASE, fatal: errorMessage(error) }, null, 2));
  process.exitCode = 1;
});
