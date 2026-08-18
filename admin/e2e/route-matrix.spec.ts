import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { ADMIN_ROUTE_CATALOG } from "../src/lib/admin-route-catalog";

const ADMIN_ROUTES = ADMIN_ROUTE_CATALOG.map(({ path }) =>
  path.replace(/\[[^\]]+\]/g, "demo"),
);

type RouteEvidenceRecord = {
  requestedRoute: string;
  finalPath: string;
  httpStatus: number | null;
  viewport: { width: number; height: number };
  states: string[];
  canonicalStates: string[];
  layout: {
    documentScrollWidth: number;
    bodyScrollWidth: number;
    overflowPx: number;
  };
  accessibility: {
    h1Count: number;
    focusableCount: number;
    skipLinkCount: number;
    skipLinkText: string | null;
    skipLinkFirstFocused: boolean;
    skipLinkFocusIndicatorVisible: boolean;
    skipLinkObscured: boolean;
    skipTarget: string | null;
    skipTargetFocused: boolean;
  };
  reducedMotion: {
    longRunningAnimations: number;
    contentPreserved: boolean;
    textLengthBefore: number;
    textLengthAfter: number;
  };
  forbiddenSurface: {
    fixtureMarkers: string[];
    rawJsonMarkers: string[];
    snakeCaseMarkers: string[];
    oldBrandMarkers: string[];
  };
  failures: string[];
  screenshot: string;
};

const CANONICAL_STATE_ALIASES: Record<string, string> = {
  empty: "empty",
  error: "error",
  forbidden: "unauthorized",
  generating: "processing",
  loading: "loading",
  locked: "locked",
  "need-login": "unauthorized",
  pending: "processing",
  preparing: "processing",
  processing: "processing",
  queued: "processing",
  submitting: "processing",
  unauthorized: "unauthorized",
  unavailable: "unavailable",
  validating: "processing",
};

function canonicalStates(states: string[]): string[] {
  return Array.from(
    new Set(states.map((state) => CANONICAL_STATE_ALIASES[state]).filter(Boolean)),
  ).sort();
}

function routeEvidenceFileName(route: string, index: number): string {
  const label =
    route === "/"
      ? "home"
      : route.replace(/^\/+/, "").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-|-$/g, "") ||
        "route";
  return `${String(index + 1).padStart(3, "0")}-${label}.jpg`;
}

test("Admin route catalog has no critical browser failures or horizontal overflow", async ({
  page,
}, testInfo) => {
  test.setTimeout(15 * 60_000);
  let currentRoute = "";
  const browserErrors: string[] = [];
  const criticalHttpErrors: string[] = [];
  const failures: string[] = [];
  const evidenceRoot = process.env.ROUTE_EVIDENCE_DIR
    ? resolve(process.env.ROUTE_EVIDENCE_DIR)
    : undefined;
  const evidenceRecords: RouteEvidenceRecord[] = [];

  page.on("pageerror", (error) => browserErrors.push(`${currentRoute}: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
      browserErrors.push(`${currentRoute}: ${message.text()}`);
    }
  });
  page.on("response", (resource) => {
    if (resource.status() < 400) return;
    const request = resource.request();
    if (["document", "script", "stylesheet", "font", "image"].includes(request.resourceType())) {
      criticalHttpErrors.push(`${currentRoute}: ${resource.status()} ${request.resourceType()} ${resource.url()}`);
    }
  });

  const adminEmail = process.env.ROUTE_EVIDENCE_ADMIN_EMAIL;
  const adminPassword = process.env.ROUTE_EVIDENCE_ADMIN_PASSWORD;
  if (adminEmail && adminPassword) {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.getByLabel("工作邮箱").fill(adminEmail);
    await page.getByLabel("密码").fill(adminPassword);
    const loginResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST"
        && new URL(response.url()).pathname === "/api/v1/admin/auth/login",
    );
    await page.getByRole("button", { name: "进入运营台" }).click();
    const response = await loginResponse;
    if (!response.ok()) failures.push(`Admin evidence login failed with HTTP ${response.status()}`);
    await page.waitForURL((url) => url.pathname !== "/login");
  }

  for (const route of ADMIN_ROUTES) {
    currentRoute = route;
    const routeFailures: string[] = [];
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);
    if (!response) routeFailures.push(`${route}: document response missing`);
    if (response && !response.ok()) {
      routeFailures.push(`${route}: document HTTP ${response.status()}`);
    }
    await expect(page.locator("body")).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      height: window.innerHeight,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    const overflowPx = Math.max(dimensions.document, dimensions.body) - dimensions.viewport;
    if (overflowPx > 1) routeFailures.push(`${route}: page overflow ${overflowPx}px`);

    const h1Count = await page.locator("h1:visible").count();
    if (h1Count !== 1) routeFailures.push(`${route}: expected one visible h1, found ${h1Count}`);

    const skipLinks = page.locator('a[href^="#"]').filter({ hasText: /跳到/ });
    const skipLinkCount = await skipLinks.count();
    let skipLinkText: string | null = null;
    let skipLinkFirstFocused = false;
    let skipLinkFocusIndicatorVisible = false;
    let skipLinkObscured = false;
    let skipTarget: string | null = null;
    let skipTargetFocused = false;
    if (skipLinkCount === 1) {
      const skipLink = skipLinks.first();
      skipLinkText = (await skipLink.textContent())?.replace(/\s+/g, " ").trim() ?? null;
      skipTarget = await skipLink.getAttribute("href");
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);
      const focusState = await skipLink.evaluate((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const centerX = Math.min(window.innerWidth - 1, Math.max(0, rect.left + rect.width / 2));
        const centerY = Math.min(window.innerHeight - 1, Math.max(0, rect.top + rect.height / 2));
        const top = document.elementFromPoint(centerX, centerY);
        return {
          focused: document.activeElement === element,
          indicator:
            (style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) >= 2)
            || style.boxShadow !== "none",
          obscured: Boolean(top && top !== element && !element.contains(top) && !top.contains(element)),
        };
      });
      skipLinkFirstFocused = focusState.focused;
      skipLinkFocusIndicatorVisible = focusState.indicator;
      skipLinkObscured = focusState.obscured;
      if (!skipLinkFirstFocused) routeFailures.push(`${route}: Skip Link is not first keyboard focus`);
      if (!skipLinkFocusIndicatorVisible) routeFailures.push(`${route}: Skip Link lacks a visible focus indicator`);
      if (skipLinkObscured) routeFailures.push(`${route}: Skip Link focus is obscured`);
      if (skipLinkFirstFocused && skipTarget) {
        await page.keyboard.press("Enter");
        skipTargetFocused = await page.evaluate((selector) => {
          const target = document.querySelector(selector);
          return Boolean(target && document.activeElement === target);
        }, skipTarget);
        if (!skipTargetFocused) routeFailures.push(`${route}: Skip Link target did not receive focus`);
      }
    } else {
      routeFailures.push(`${route}: expected one Skip Link, found ${skipLinkCount}`);
    }

    const focusableCount = await page.locator(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ).count();
    if (focusableCount === 0) routeFailures.push(`${route}: no keyboard-reachable controls`);

    const forbiddenSurface = await page.evaluate(() => {
      const text = document.body.innerText;
      const unique = (values: string[]) => Array.from(new Set(values)).slice(0, 12);
      return {
        fixtureMarkers: unique(text.match(/UI 演示数据|演示 Fixture|\bfixture\b/gi) ?? []),
        rawJsonMarkers: unique(text.match(/raw\s*json|(?:^|\n)\s*[\[{]\s*["'][A-Za-z0-9_-]+["']\s*:/gim) ?? []),
        snakeCaseMarkers: unique(text.match(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g) ?? []),
        oldBrandMarkers: unique(text.match(/\bFateRadar\b|fateradar\.[a-z.]+/gi) ?? []),
      };
    });
    for (const [kind, matches] of Object.entries(forbiddenSurface)) {
      if (matches.length > 0) routeFailures.push(`${route}: ${kind} ${matches.join(", ")}`);
    }

    const textLengthBefore = await page.locator("body").innerText().then((text) => text.length);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForTimeout(60);
    const reducedMotion = await page.evaluate((before) => {
      const after = document.body.innerText.length;
      return {
        longRunningAnimations: document.getAnimations().filter((animation) => {
          const duration = animation.effect?.getComputedTiming().duration;
          return typeof duration === "number" && duration > 50;
        }).length,
        contentPreserved: after === before,
        textLengthBefore: before,
        textLengthAfter: after,
      };
    }, textLengthBefore);
    if (reducedMotion.longRunningAnimations > 0) {
      routeFailures.push(`${route}: ${reducedMotion.longRunningAnimations} long animations under reduced motion`);
    }
    if (!reducedMotion.contentPreserved) routeFailures.push(`${route}: content changed under reduced motion`);
    await page.emulateMedia({ reducedMotion: "no-preference" });

    if (evidenceRoot) {
      const screenshotPath = resolve(
        evidenceRoot,
        testInfo.project.name,
        "screenshots",
        routeEvidenceFileName(route, evidenceRecords.length),
      );
      await mkdir(dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, type: "jpeg", quality: 65 });
      const states = await page.locator("[data-state]").evaluateAll((elements) =>
        Array.from(
          new Set(
            elements
              .map((element) => element.getAttribute("data-state"))
              .filter((state): state is string => state !== null),
          ),
        ).sort(),
      );
      evidenceRecords.push({
        requestedRoute: route,
        finalPath: new URL(page.url()).pathname,
        httpStatus: response?.status() ?? null,
        viewport: { width: dimensions.viewport, height: dimensions.height },
        states,
        canonicalStates: canonicalStates(states),
        layout: {
          documentScrollWidth: dimensions.document,
          bodyScrollWidth: dimensions.body,
          overflowPx,
        },
        accessibility: {
          h1Count,
          focusableCount,
          skipLinkCount,
          skipLinkText,
          skipLinkFirstFocused,
          skipLinkFocusIndicatorVisible,
          skipLinkObscured,
          skipTarget,
          skipTargetFocused,
        },
        reducedMotion,
        forbiddenSurface,
        failures: routeFailures,
        screenshot: relative(evidenceRoot, screenshotPath),
      });
    }
    failures.push(...routeFailures);
  }

  failures.push(...browserErrors, ...criticalHttpErrors);

  if (process.env.ROUTE_EVIDENCE_DIR) {
    const generatedAt = new Date().toISOString();
    const reviewedAt = process.env.ROUTE_EVIDENCE_REVIEWED_AT ?? null;
    await writeFile(
      resolve(evidenceRoot!, `${testInfo.project.name}.json`),
      `${JSON.stringify(
        {
          schema: "mingli.route-evidence/v1",
          app: "admin",
          gitCommit: process.env.GIT_COMMIT ?? "not-provided",
          generatedAt,
          reviewedAt,
          reviewStatus: reviewedAt ? "reviewed" : "automated-only",
          test: {
            file: relative(process.cwd(), testInfo.file),
            name: testInfo.title,
            checks: [
              "http-200",
              "critical-browser-errors",
              "horizontal-overflow<=1px",
              "one-visible-h1",
              "skip-link-first-focus",
              "focus-indicator-visible",
              "focused-content-unobscured",
              "keyboard-target-reachable",
              "reduced-motion-static-content-preserved",
              "forbidden-surface-markers-absent",
            ],
          },
          baseURL: process.env.ADMIN_BASE_URL ?? "http://127.0.0.1:3001",
          project: testInfo.project.name,
          failures,
          routes: evidenceRecords,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
    expect(
      existsSync(resolve(evidenceRoot!, `${testInfo.project.name}.json`)),
      "ROUTE_EVIDENCE_DIR requires a route evidence manifest",
    ).toBe(true);
  }
  expect(failures, failures.join("\n")).toEqual([]);
});

test("Admin UI Lab remains absent from the production route surface", async ({ page }) => {
  const response = await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  expect(response?.status()).toBe(404);
});

test("Admin login skip link moves keyboard focus to the main content", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  const skipLink = page.getByRole("link", { name: "跳到主要内容" });

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#admin-login-main")).toBeFocused();
});

test("Admin navigation exposes every static route from the catalog", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const expected = ADMIN_ROUTE_CATALOG.filter(
    (route) => route.navigation !== false && !route.path.includes("["),
  ).map((route) => route.path);
  const actual = await page.locator('nav[aria-label="运营导航"] a').evaluateAll((links) =>
    links.map((link) => link.getAttribute("href")),
  );

  expect(actual).toEqual(expected);
});
