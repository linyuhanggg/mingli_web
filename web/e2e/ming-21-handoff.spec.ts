import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page, type Route } from "@playwright/test";

const WAITING_READING_ID = "ming-21-waiting-reading";
const BAZI_WAITING_READING_ID = "ming-21-bazi-waiting-reading";
let waitingStartedAt = new Date().toISOString();
type ApiState = { profiles: Array<Record<string, unknown>> };
const apiStateByPage = new WeakMap<Page, ApiState>();

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
  let draftLabel = "";
  const state: ApiState = { profiles: [] };
  apiStateByPage.set(page, state);

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
      await json(route, { profiles: state.profiles });
      return;
    }
    if (method === "POST" && path === "/api/v1/profiles/drafts") {
      const body = request.postDataJSON() as { label?: string };
      draftLabel = body.label?.trim() ?? "";
      await json(route, {
        draft_id: "11111111-1111-4111-8111-111111111111",
        status: "draft",
      });
      return;
    }
    if (
      method === "POST"
      && path === "/api/v1/profiles/drafts/11111111-1111-4111-8111-111111111111/confirm"
    ) {
      const body = request.postDataJSON() as { birth_datetime?: string };
      state.profiles = [
        {
          profile_id: "22222222-2222-4222-8222-222222222222",
          profile_version_id: "33333333-3333-4333-8333-333333333333",
          subject_ref: "profile-version:33333333-3333-4333-8333-333333333333",
          version: 1,
          display_name: draftLabel,
          birth_date: body.birth_datetime?.slice(0, 10) ?? null,
          created_at: "2026-08-25T00:00:00Z",
        },
      ];
      await json(route, state.profiles[0]);
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

function seedProfiles(page: Page, profiles: ApiState["profiles"]) {
  const state = apiStateByPage.get(page);
  if (!state) throw new Error("API mocks must be installed before seeding profiles");
  state.profiles = profiles;
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

test("profile empty state completes the canonical creation flow", async ({
  page,
}, testInfo) => {
  await page.goto("/account/profiles", { waitUntil: "domcontentloaded" });

  const createLink = page.getByRole("link", { name: "开始建立档案" });
  await expect(page.getByRole("heading", { name: "还没有已保存的档案" })).toBeVisible();
  await expect(page.getByText("保存第一份出生资料后，这里会成为你的档案柜。")).toBeVisible();
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} profile empty state`);
  await screenshot(page, testInfo.project.name, "profile-empty");

  await createLink.click();
  await expect(page).toHaveURL(/\/account\/profiles\/new$/);
  await expect(page.getByRole("heading", { name: "建立命理档案" })).toBeVisible();

  await page.getByLabel("档案名称").fill("四视口验收档案");
  await page.getByLabel("出生时间").fill("1992-06-18T09:30");
  await page.getByLabel("出生地点").fill("浙江省杭州市");
  await page.getByLabel("性别").selectOption("female");
  await page.getByLabel("时间口径").selectOption("civil");
  await page.getByLabel("子时口径").selectOption("midnight");
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} profile form`);
  await screenshot(page, testInfo.project.name, "profile-form-complete");

  await page.getByRole("button", { name: "保存档案" }).click();
  await expect(page).toHaveURL(/\/account\/profiles\?created=1$/);
  await expect(
    page.getByRole("status", { name: "“四视口验收档案”已保存" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "已保存的档案" })).toBeVisible();
  await expect(page.getByText("四视口验收档案", { exact: true })).toBeVisible();
  const savedAction = page.getByRole("link", { name: "用这份档案排八字" });
  await expect(savedAction).toHaveCount(2);
  await expect(savedAction.first()).toHaveAttribute(
    "href",
    "/app/bazi?profile=33333333-3333-4333-8333-333333333333",
  );
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} saved profile list`);
  await screenshot(page, testInfo.project.name, "profile-saved");

  await page.getByRole("link", { name: "新建档案" }).click();
  await page.getByLabel("档案名称").fill("四视口验收档案");
  await page.getByLabel("出生时间").fill("1992-06-18T09:30");
  await page.getByLabel("出生地点").fill("浙江省杭州市");
  await page.getByLabel("性别").selectOption("female");
  await page.getByLabel("时间口径").selectOption("civil");
  await page.getByLabel("子时口径").selectOption("midnight");
  const saveProfile = page.getByRole("button", { name: "保存档案" });
  await saveProfile.click();

  const update = page.getByRole("button", { name: "更新“四视口验收档案”" });
  await expect(page.getByRole("dialog", { name: "已有同名档案“四视口验收档案”" })).toBeVisible();
  await expect(update).toBeFocused();
  await expect(update).toHaveAttribute("data-variant", "primary");
  await expect(page.getByRole("group", { name: "另存为新档案" })).toHaveAttribute(
    "data-variant",
    "secondary-card",
  );
  await expect(page.getByRole("button", { name: "另存为新档案" })).toHaveAttribute(
    "data-variant",
    "secondary",
  );
  const cancel = page.getByRole("button", { name: "取消" });
  await expect(cancel).toHaveAttribute("data-variant", "ghost");
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} profile conflict dialog`);
  await screenshot(page, testInfo.project.name, "profile-conflict");
  await cancel.click();
  await expect(saveProfile).toBeFocused();
});

test("mobile input geometry and recoverable reading waiting state stay usable", async ({
  page,
}, testInfo) => {
  seedProfiles(page, [
    {
      profile_id: "44444444-4444-4444-8444-444444444444",
      profile_version_id: "55555555-5555-4555-8555-555555555555",
      subject_ref: "profile-version:55555555-5555-4555-8555-555555555555",
      version: 2,
      display_name: "四视口档案",
      birth_date: "1992-06-18",
      created_at: "2026-08-25T01:00:00Z",
    },
    {
      profile_id: "66666666-6666-4666-8666-666666666666",
      profile_version_id: "77777777-7777-4777-8777-777777777777",
      subject_ref: "profile-version:77777777-7777-4777-8777-777777777777",
      version: 1,
      display_name: "仅有名称",
      birth_date: null,
      created_at: "2026-08-24T01:00:00Z",
    },
  ]);
  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("button", { name: /^免费排盘/ })).toBeVisible();
  const profileSelect = page.getByRole("combobox", { name: "排盘资料" });
  await expect(profileSelect.locator("option").nth(0)).toHaveText("四视口档案 · 1992-06-18");
  await expect(profileSelect.locator("option").nth(1)).toHaveText(/^档案 1 · /);
  await expect(page.getByText("将直接使用这份已保存资料；如出生信息有变化，选重新录入。")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(
    /verified_exact|ViewModel|不可变|落库|接纳|句柄|payment_id/,
  );
  await screenshot(page, testInfo.project.name, "bazi-profile-friendly");
  await profileSelect.selectOption("77777777-7777-4777-8777-777777777777");
  await expect(profileSelect).toHaveValue("77777777-7777-4777-8777-777777777777");
  await screenshot(page, testInfo.project.name, "bazi-profile-fallback");
  await profileSelect.selectOption("");
  await expect(page.getByText("将核对出生资料并保存为新档案。")).toBeVisible();
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
  const progress = page.getByRole("list", { name: "排盘进度阶段" });
  await expect(progress).toContainText("资料已提交");
  await expect(progress.locator('[aria-current="step"]')).toHaveText("资料已提交");
  await expect(page.locator("body")).not.toContainText(
    /verified_exact|ViewModel|不可变|落库|接纳|句柄|payment_id/,
  );
  await expectNoHorizontalOverflow(page, `${testInfo.project.name} waiting state`);
  await screenshot(page, testInfo.project.name, "reading-waiting");
});
