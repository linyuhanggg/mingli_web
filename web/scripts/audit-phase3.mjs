/**
 * One-shot phase-3 browser audit (account / 我的, 2026-08-15).
 *
 * The script only visits the already-running local dev server and uses the
 * system Chrome executable. It never starts or stops the server.
 */
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "http://127.0.0.1:3000";
const ROUTES = [
  ["/account", "account"],
  ["/account/profiles", "profiles"],
  ["/account/history", "history"],
  ["/account/orders", "orders"],
  ["/account/notifications", "notifications"],
  ["/account/settings", "settings"],
  ["/account/invites", "invites"],
  ["/account/data-rights", "data-rights"],
];
const VIEWPORTS = [360, 768, 1024, 1440];
const OUT_ROOT = path.join(ROOT, "e2e", "screenshots", "audit-2026-08-14", "phase3");
const GUEST_ACCOUNT_RESPONSE = JSON.stringify({ title: "Authentication required" });
const GUEST_SESSION_RESPONSE = JSON.stringify({ csrf_token: "audit-guest-csrf-token" });

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

function addFailure(entry, check, reason) {
  entry.failures.push({ check, reason });
}

async function assertPageContract(page, entry, route) {
  const landmarks = await page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0;
    };
    const mains = [...document.querySelectorAll("main")].filter(visible);
    const h1s = mains.flatMap((main) => [...main.querySelectorAll("h1")].filter(visible));
    return {
      mainCount: mains.length,
      h1Count: h1s.length,
      h1Text: h1s.map((heading) => heading.textContent?.trim() ?? ""),
    };
  });
  entry.landmarks = landmarks;

  if (landmarks.mainCount !== 1) {
    addFailure(entry, "main-landmark", `expected one visible main, found ${landmarks.mainCount}`);
  }
  if (landmarks.h1Count !== 1) {
    addFailure(entry, "h1-landmark", `expected one visible h1 in main, found ${landmarks.h1Count}`);
  }
  if (route === "/account" && landmarks.h1Text[0] !== "我的") {
    addFailure(entry, "account-h1", `expected h1 我的, received ${JSON.stringify(landmarks.h1Text[0])}`);
  }

  if (route === "/account") {
    const identity = page.getByRole("heading", { name: "游客模式", exact: true });
    if ((await identity.count()) !== 1 || !(await identity.isVisible())) {
      addFailure(entry, "guest-identity", "expected the guest identity card in a fresh browser context");
    }
    const navigation = page.getByRole("navigation", { name: "我的账户入口", exact: true });
    const navigationCount = await navigation.count();
    if (navigationCount !== 1 || !(await navigation.isVisible())) {
      addFailure(entry, "account-shortcuts", `expected one visible account shortcut nav, found ${navigationCount}`);
    } else {
      const links = navigation.getByRole("link");
      if (await links.count() !== 6) {
        addFailure(entry, "account-shortcuts", `expected six account shortcuts, found ${await links.count()}`);
      }
    }
    if ((await page.getByRole("heading", { name: "登录后开始使用", exact: true }).count()) !== 1) {
      addFailure(entry, "guest-login-entry", "expected the signed-out login entry");
    }
  } else if ((await page.getByRole("heading", { name: "需要登录", exact: true }).count()) !== 1) {
    addFailure(entry, "private-gate", "expected the signed-out subpage gate");
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
      await context.route("**/api/v1/account", async (route) => {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: GUEST_ACCOUNT_RESPONSE,
        });
      });
      await context.route("**/api/v1/guest-sessions", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: GUEST_SESSION_RESPONSE,
        });
      });
      const page = await context.newPage();

      try {
        for (const [route, name] of ROUTES) {
          const entry = { viewport, route, failures: [] };
          const screenshotPath = path.join(OUT_ROOT, String(viewport), `${name}.png`);
          const runtimeErrors = [];
          page.removeAllListeners("pageerror");
          page.on("pageerror", (error) => runtimeErrors.push(errorMessage(error)));

          try {
            const response = await page.goto(BASE + route, {
              waitUntil: "networkidle",
              timeout: 45000,
            });
            await page.waitForTimeout(300);
            entry.httpStatus = response ? response.status() : null;
            entry.finalUrl = page.url();
            entry.finalPathname = new URL(page.url()).pathname;

            if (entry.finalPathname !== route) {
              addFailure(entry, "final-url", `expected ${route}, received ${entry.finalPathname}`);
            }

            const layout = await page.evaluate(() => ({
              scrollWidth: document.documentElement.scrollWidth,
              innerWidth: window.innerWidth,
            }));
            entry.layout = { ...layout, overflow: layout.scrollWidth - layout.innerWidth };
            if (layout.scrollWidth > layout.innerWidth + 1) {
              addFailure(
                entry,
                "horizontal-overflow",
                `scrollWidth ${layout.scrollWidth}px exceeds innerWidth ${layout.innerWidth}px`,
              );
            }

            await assertPageContract(page, entry, route);
          } catch (error) {
            addFailure(entry, "route-audit", errorMessage(error));
          }

          if (runtimeErrors.length > 0) {
            entry.runtimeErrors = runtimeErrors;
            addFailure(entry, "runtime-errors", runtimeErrors.join(" | "));
          }

          try {
            fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
            await page.screenshot({ path: screenshotPath, fullPage: true });
            entry.screenshot = path.relative(ROOT, screenshotPath);
          } catch (error) {
            addFailure(entry, "screenshot", errorMessage(error));
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
    state: "signed-out",
    responseInterception: "The real browser audit explicitly returns 401 for the account probe and a CSRF token for the guest login form; no user or business fixture data is injected.",
    total: results.length,
    passed: results.length - failures.length,
    failed: failures.length,
    results,
  };
  fs.mkdirSync(OUT_ROOT, { recursive: true });
  fs.writeFileSync(path.join(OUT_ROOT, "report.json"), JSON.stringify(report, null, 2));

  console.log(JSON.stringify(report, null, 2));
  console.log(`phase-3 audit: ${report.passed}/${report.total} route/viewport combinations passed`);
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
