import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";

import { expect, test } from "@playwright/test";

const WEB_ROUTES = [
  "/",
  "/about",
  "/account",
  "/account/data-rights",
  "/account/entitlements",
  "/account/history",
  "/account/history/demo-root",
  "/account/invitations",
  "/account/invites",
  "/account/notifications",
  "/account/orders",
  "/account/profiles",
  "/account/profiles/demo-profile",
  "/account/settings",
  "/account/settings/preferences",
  "/account/settings/privacy-data",
  "/account/settings/security",
  "/app",
  "/app/ask/liuyao",
  "/app/bazi",
  "/app/fortune/today",
  "/app/fortune/week",
  "/app/profile/new",
  "/app/profiles",
  "/app/readings",
  "/app/readings/demo-reading",
  "/arts",
  "/auth/consent",
  "/auth/login",
  "/auth/recover",
  "/auth/register",
  "/auth/set-password",
  "/auth/verify",
  "/bazi",
  "/bazi/hepan",
  "/canwen",
  "/checkout",
  "/checkout/demo-order",
  "/daily",
  "/daliuren",
  "/fengshui",
  "/hecan",
  "/invite/demo-code",
  "/jianxiang",
  "/library",
  "/library/demo-article",
  "/liuyao",
  "/luming-nayin",
  "/meihua",
  "/methodology",
  "/pricing",
  "/privacy",
  "/qimen",
  "/qizheng",
  "/qizheng/hepan",
  "/selection",
  "/share/demo-share",
  "/support",
  "/taiyi",
  "/terms",
  "/tools",
  "/tools/chart-similarity",
  "/tools/dream",
  "/tools/five-elements",
  "/tools/name",
  "/tools/rhythm",
  "/tools/time-check",
  "/wenshi",
  "/workbench/demo-handle",
  "/ziwei",
  "/ziwei/hepan",
] as const;

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
    workbenchRightPaneWidthPx: number | null;
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

test("public and private route matrix has no critical browser failures or horizontal overflow", async ({
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

  for (const route of WEB_ROUTES) {
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

    const workbenchRightPaneWidthPx = await page.evaluate(() => {
      const workspace = document.querySelector('[data-layout="workbench-workspace"]');
      if (!(workspace instanceof HTMLElement) || workspace.children.length < 2) return null;
      const first = workspace.children[0].getBoundingClientRect();
      const second = workspace.children[1].getBoundingClientRect();
      const isTwoColumn = Math.abs(first.top - second.top) <= 2 && second.left > first.left;
      return isTwoColumn ? Math.round(second.width * 100) / 100 : null;
    });
    if (workbenchRightPaneWidthPx !== null && workbenchRightPaneWidthPx < 360) {
      routeFailures.push(`${route}: workbench reading pane ${workbenchRightPaneWidthPx}px below 360px`);
    }

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
          workbenchRightPaneWidthPx,
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
          app: "web",
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
              "workbench-right-pane>=360px",
              "one-visible-h1",
              "skip-link-first-focus",
              "focus-indicator-visible",
              "focused-content-unobscured",
              "keyboard-target-reachable",
              "reduced-motion-static-content-preserved",
              "forbidden-surface-markers-absent",
            ],
          },
          baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
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

test("placeholder tool routes expose readonly input contracts without pretending to submit", async ({
  page,
}) => {
  const tools = [
    { route: "/tools/dream", title: "解梦", fields: ["梦境内容", "现实背景"] },
    { route: "/tools/name", title: "姓名分析", fields: ["姓名", "使用场景"] },
  ] as const;

  for (const tool of tools) {
    await page.goto(tool.route, { waitUntil: "domcontentloaded" });
    const form = page.getByRole("form", { name: `${tool.title}输入` });

    await expect(form).toBeVisible();
    for (const field of tool.fields) {
      await expect(form.getByLabel(field)).toHaveAttribute("readonly");
    }
    await expect(form.getByRole("button", { name: "提交暂未开放" })).toBeDisabled();
    await expect(form).toContainText("不会提交或保存资料");
    await expect(page.getByRole("status", { name: `${tool.title}暂不可用` })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
  }
});

test("UI Lab remains absent from the production route surface", async ({ page }) => {
  const response = await page.goto("/_ui-lab", { waitUntil: "domcontentloaded" });
  expect(response?.status()).toBe(404);
});

test("public skip link moves keyboard focus to the main content", async ({ page }) => {
  await page.goto("/methodology", { waitUntil: "domcontentloaded" });
  const skipLink = page.getByRole("link", { name: "跳到主要内容" });

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("private skip link moves keyboard focus to the private main content", async ({ page }) => {
  await page.goto("/account", { waitUntil: "domcontentloaded" });
  const skipLink = page.getByRole("link", { name: "跳到主要内容" });

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#private-main")).toBeFocused();
});

test("public navigation switches at the frozen 767/768px boundary", async ({ page }) => {
  await page.setViewportSize({ width: 767, height: 800 });
  await page.goto("/methodology", { waitUntil: "domcontentloaded" });
  await expect(page.locator('nav[aria-label="主导航"]')).toBeHidden();
  await expect(page.locator('nav[aria-label="移动底栏"]')).toBeVisible();

  await page.setViewportSize({ width: 768, height: 800 });
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator('nav[aria-label="主导航"]')).toBeVisible();
  await expect(page.locator('nav[aria-label="移动底栏"]')).toBeHidden();
});

test("policy pages publish their preview state and real entry links", async ({ page }) => {
  for (const route of ["/privacy", "/terms"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const metadata = page.getByRole("region", { name: "政策版本" });

    await expect(metadata).toBeVisible();
    await expect(metadata.getByText("开发预览 v0.1")).toBeVisible();
    await expect(metadata.getByText("未生效")).toBeVisible();
    await expect(metadata.getByRole("link", { name: "前往登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    await expect(metadata.getByRole("link", { name: "查看价格与交付" })).toHaveAttribute(
      "href",
      "/pricing",
    );
  }
});

test("auth and commerce routes keep policy navigation reachable", async ({ page }) => {
  const routes = [
    { route: "/auth/login", navigation: "其他认证入口" },
    { route: "/auth/register", navigation: "其他认证入口" },
    { route: "/checkout", navigation: "购买相关政策" },
    { route: "/checkout/demo-order", navigation: "购买相关政策" },
  ] as const;

  for (const { route, navigation } of routes) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const policyNav = page.getByRole("navigation", { name: navigation });

    await expect(policyNav.getByRole("link", { name: "查看隐私政策" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    await expect(policyNav.getByRole("link", { name: "查看服务条款" })).toHaveAttribute(
      "href",
      "/terms",
    );
  }
});

test("support explains the password-first identity flow", async ({ page }) => {
  await page.goto("/support", { waitUntil: "domcontentloaded" });
  const main = page.locator("#main-content");

  await expect(main).toContainText("密码主登录");
  await expect(main).toContainText("OTP 用于注册验证、快捷登录和找回密码");
  await expect(main).toContainText("OTP 核验后设置密码");
  await expect(main).not.toContainText("不需要另设注册密码");
});

test("account explains the password-first identity flow", async ({ page }) => {
  await page.goto("/account", { waitUntil: "domcontentloaded" });
  const main = page.locator("#private-main");

  await expect(main).toContainText("密码是默认登录方式");
  await expect(main).toContainText("OTP 快捷登录");
  await expect(main).toContainText("OTP 用于注册验证、快捷登录和找回密码");
  await expect(main).toContainText("OTP 核验后设置密码");

  await expect(main).not.toContainText("首次邮箱验证自动注册");
  await expect(main).not.toContainText("已有邮箱直接登录");
});

test("private document responses are not cacheable or indexable", async ({ page }) => {
  for (const route of ["/app", "/account", "/account/history/demo-root"]) {
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response, `${route} did not return a response`).not.toBeNull();
    expect(response?.headers()["cache-control"], route).toBe(
      "private, no-store, max-age=0",
    );
    expect(response?.headers()["x-robots-tag"], route).toBe("noindex, nofollow, noarchive");
  }
});
