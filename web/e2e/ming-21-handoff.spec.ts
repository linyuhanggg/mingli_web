import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page, type Route } from "@playwright/test";

const WAITING_READING_ID = "ming-21-waiting-reading";
const BAZI_WAITING_READING_ID = "ming-21-bazi-waiting-reading";
let waitingStartedAt = new Date().toISOString();

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function waitingSummary(readingId = WAITING_READING_ID, productId = "meihua") {
  return {
    reading_version_id: readingId,
    reading_root_id: `${readingId}-root`,
    profile_version_id: productId === "bazi" ? "ming-21-bazi-profile-version" : null,
    capability_id: productId,
    product_id: productId,
    runtime_capability_ids: [productId],
    version: 1,
    status: "input_ready",
    object_id: "event",
    dimension_ids: ["overview"],
    horizon: { kind_id: "now", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: waitingStartedAt,
  };
}

async function installApiMocks(page: Page) {
  await page.context().addCookies([
    {
      name: "mingli_csrf",
      value: "ming-21-browser-evidence-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;

    if (method === "GET" && path === "/api/v1/account") {
      await json(route, {
        user_id: "ming-21-browser-user",
        identities: [
          {
            id: "ming-21-browser-identity",
            provider: "email",
            masked_destination: "ming***@example.com",
            verified_at: "2026-08-25T00:00:00Z",
          },
        ],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/profiles") {
      await json(route, { profiles: [] });
      return;
    }
    if (method === "GET" && path === `/api/v1/readings/${WAITING_READING_ID}`) {
      await json(route, waitingSummary());
      return;
    }
    if (method === "GET" && path === `/api/v1/readings/${BAZI_WAITING_READING_ID}`) {
      await json(route, waitingSummary(BAZI_WAITING_READING_ID, "bazi"));
      return;
    }
    await json(route, { title: "Unhandled e2e API", detail: `${method} ${path}` }, 599);
  });
}

async function expectNoHorizontalOverflow(page: Page, label: string) {
  const width = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(width.document, `${label} horizontal overflow`).toBeLessThanOrEqual(width.viewport + 1);
}

async function screenshot(page: Page, viewport: string, name: string) {
  const directory = resolve(
    process.env.BROWSER_EVIDENCE_DIR
      ?? resolve(process.cwd(), "e2e/screenshots/2026-08-25-ming-21"),
    viewport,
  );
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: resolve(directory, `${name}.png`),
    animations: "disabled",
    fullPage: true,
  });
}

test.beforeEach(async ({ page }) => {
  waitingStartedAt = new Date().toISOString();
  await installApiMocks(page);
});

test("profile empty state preserves the base creation boundary", async ({
  page,
}, testInfo) => {
  await page.goto("/account/profiles", { waitUntil: "domcontentloaded" });

  const createLink = page.getByRole("link", { name: "开始建立档案" });
  await expect(page.getByRole("heading", { name: "还没有已保存的档案" })).toBeVisible();
  await expect(createLink).toHaveAttribute("href", "/app/profile/new");
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} profile empty state`);
  await screenshot(page, testInfo.project.name, "profile-empty");
});

test("mobile input geometry and recoverable reading waiting state stay usable", async ({
  page,
}, testInfo) => {
  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("button", { name: /^立即排盘（免费）/ })).toBeVisible();
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} bazi input`);

  if (testInfo.project.name === "360") {
    const bottomBar = page.getByRole("navigation", { name: "移动底栏" });
    await expect(bottomBar).toBeVisible();
    const bottomBarBox = await bottomBar.boundingBox();
    expect(bottomBarBox).not.toBeNull();
    for (const label of ["出生年份", "出生月份", "出生日期", "出生小时", "出生分钟"]) {
      const field = page.getByLabel(label);
      await expect(field).toBeVisible();
      const box = await field.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x, label).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width, label).toBeLessThanOrEqual(360);
      expect(box!.y + box!.height, label).toBeLessThanOrEqual(bottomBarBox!.y);
    }
  }
  await screenshot(page, testInfo.project.name, "bazi-input");

  await page.evaluate(({ readingId, startedAt }) => {
    window.sessionStorage.setItem(
      "mingli.recoverable-reading.v3.bazi",
      JSON.stringify({
        version: 3,
        product_id: "bazi",
        reading_version_id: readingId,
        started_at: startedAt,
        expires_at: Date.now() + 30 * 60 * 1000,
        submission: {
          profile_version_id: "ming-21-bazi-profile-version",
          values: { issue: "测试八字等待恢复", targetYear: "2028" },
        },
      }),
    );
  }, {
    readingId: BAZI_WAITING_READING_ID,
    startedAt: Date.parse(waitingStartedAt),
  });
  await page.goto("/bazi", { waitUntil: "domcontentloaded" });

  const baziWaiting = page.getByRole("status").filter({ hasText: "正在为你排盘" });
  await expect(baziWaiting).toBeVisible();
  await expect(baziWaiting).toContainText("通常需要 5–15 秒");
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} bazi waiting state`);
  await screenshot(page, testInfo.project.name, "bazi-waiting");

  await page.evaluate(({ readingId, startedAt }) => {
    window.sessionStorage.setItem(
      "mingli.recoverable-reading.v3.meihua",
      JSON.stringify({
        version: 3,
        product_id: "meihua",
        reading_version_id: readingId,
        started_at: startedAt,
        expires_at: Date.now() + 30 * 60 * 1000,
        submission: {
          values: {
            issue: "测试等待恢复",
            focus: "outcome",
            eventTime: "2026-08-25T08:00",
            timezone: "Asia/Shanghai",
            location: "上海市",
            timeStandard: "civil",
            meihuaCastingMethod: "time",
          },
        },
      }),
    );
  }, {
    readingId: WAITING_READING_ID,
    startedAt: Date.parse(waitingStartedAt),
  });
  await page.goto("/meihua", { waitUntil: "domcontentloaded" });

  const waiting = page.getByRole("status").filter({ hasText: "正在为你排盘" });
  await expect(waiting).toBeVisible();
  await expect(waiting).toContainText("通常需要 5–15 秒");
  await expect(page.getByRole("list", { name: "排盘进度阶段" })).toContainText("资料已提交");
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} waiting state`);
  await screenshot(page, testInfo.project.name, "reading-waiting");
});
