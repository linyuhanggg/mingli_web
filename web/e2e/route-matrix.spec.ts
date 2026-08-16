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
  "/hecan",
  "/invite/demo-code",
  "/jianxiang",
  "/library",
  "/library/demo-article",
  "/liuyao",
  "/methodology",
  "/pricing",
  "/privacy",
  "/qimen",
  "/qizheng",
  "/qizheng/hepan",
  "/share/demo-share",
  "/support",
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
  screenshot: string;
};

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
  let currentRoute = "";
  const browserErrors: string[] = [];
  const criticalHttpErrors: string[] = [];
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
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response, `${route} did not return a response`).not.toBeNull();
    expect(response?.ok(), `${route} returned HTTP ${response?.status()}`).toBe(true);
    await expect(page.locator("body")).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      height: window.innerHeight,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    expect(
      Math.max(dimensions.document, dimensions.body),
      `${route} overflows ${dimensions.viewport}px viewport`,
    ).toBeLessThanOrEqual(dimensions.viewport);

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
        screenshot: relative(evidenceRoot, screenshotPath),
      });
    }
  }

  expect(browserErrors, browserErrors.join("\n")).toEqual([]);
  expect(criticalHttpErrors, criticalHttpErrors.join("\n")).toEqual([]);

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
            checks: ["http-200", "critical-browser-errors", "horizontal-overflow"],
          },
          baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
          project: testInfo.project.name,
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
});

test("tool routes expose readonly input contracts without pretending to submit", async ({
  page,
}) => {
  const tools = [
    { route: "/tools/time-check", title: "寻时定盘", fields: ["已知时间范围", "可核对事件"] },
    { route: "/tools/chart-similarity", title: "同盘匹配", fields: ["已保存盘面", "比较侧重"] },
    { route: "/tools/rhythm", title: "本命音律", fields: ["本命资料", "音律侧重"] },
    { route: "/tools/five-elements", title: "五行事实与调候", fields: ["已确认盘面", "关注主题"] },
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

  await expect(main).toContainText("密码主登录");
  await expect(main).toContainText("OTP 快捷登录");

  const otpHeading = main.getByRole("heading", { level: 2, name: "OTP 快捷登录" });
  const unavailableState = main.getByText("暂时无法确认登录状态");
  await expect
    .poll(async () => (await otpHeading.count()) > 0 || (await unavailableState.count()) > 0)
    .toBe(true);

  if (await otpHeading.count()) {
    await expect(main).toContainText("OTP 用于注册验证、快捷登录和找回密码");
    await expect(main).toContainText("OTP 核验后设置密码");
  } else {
    await expect(unavailableState).toBeVisible();
  }

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
