import { expect, test, type Page, type Route } from "@playwright/test";

type ProfileResponseMode = "loading" | "unauthorized" | "error" | "empty" | "success";

const savedProfile = {
  profile_id: "profile-e2e",
  profile_version_id: "profile-version-e2e",
  subject_ref: "profile-version:profile-version-e2e",
  version: 4,
  display_name: "测试档案甲",
  created_at: "2026-08-31T00:00:00Z",
};

async function openProfilePicker(page: Page, mode: ProfileResponseMode) {
  let releaseLoadingRequest: () => void = () => undefined;
  await page.context().addCookies([
    {
      name: "mingli_csrf",
      value: "ming92-browser-evidence-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.route("**/api/v1/account", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "ming92-e2e-user",
        identities: [],
      }),
    });
  });
  await page.route("**/api/v1/profiles", async (route: Route) => {
    if (mode === "loading") {
      await new Promise<void>((resolve) => {
        releaseLoadingRequest = resolve;
      });
      await route.abort();
      return;
    }
    if (mode === "unauthorized") {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ title: "需要登录" }),
      });
      return;
    }
    if (mode === "error") {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ title: "档案服务暂时不可用" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ profiles: mode === "success" ? [savedProfile] : [] }),
    });
  });
  await page.goto("/life-kline?state=select-profile");
  return () => releaseLoadingRequest();
}

for (const evidence of [
  { mode: "loading", heading: "正在加载档案" },
  { mode: "unauthorized", heading: "登录后选择档案" },
  { mode: "error", heading: "档案读取失败" },
  { mode: "empty", heading: "选择档案" },
  { mode: "success", heading: "选择档案" },
] as const) {
  test(`renders real profile ${evidence.mode} state`, async ({ page }, testInfo) => {
    const releaseLoadingRequest = await openProfilePicker(page, evidence.mode);

    await expect(page.getByRole("heading", { level: 2, name: evidence.heading })).toBeVisible();
    await expect(page.locator("main")).toHaveAttribute("data-view-state", "select-profile");

    if (evidence.mode === "unauthorized") {
      await expect(page.getByRole("link", { name: "登录后继续" })).toHaveAttribute(
        "href",
        "/auth/login?next=%2Flife-kline%3Fstate%3Dselect-profile",
      );
      await expect(page.getByRole("button", { name: "重新加载档案" })).toHaveCount(0);
    } else if (evidence.mode === "error") {
      await expect(page.getByRole("button", { name: "重新加载档案" })).toBeVisible();
      await expect(page.getByText("当前没有可在此页读取的档案。")).toHaveCount(0);
    } else if (evidence.mode === "empty") {
      await expect(page.getByText("当前没有可在此页读取的档案。")).toBeVisible();
    } else if (evidence.mode === "success") {
      const profileOption = page.getByRole("radio", { name: /测试档案甲/ });
      await expect(profileOption).toBeVisible();
      await expect(
        page.getByLabel("人生 K 线当前状态").getByText("版本 4"),
      ).toBeVisible();
      await profileOption.check();
      await page.getByRole("button", { name: "读取人生 K 线状态" }).click();
      await expect(
        page.getByRole("heading", { level: 2, name: "数据不足，暂不支持绘制" }),
      ).toBeVisible();
      await expect(page.locator("main")).toHaveAttribute("data-view-state", "unsupported");
      await expect(page.getByRole("button", { name: "刷新状态" })).toHaveCount(0);
      await expect(page.getByRole("button", { name: "重试" })).toHaveCount(0);
      await expect(
        page
          .getByLabel("数据不足，暂不支持绘制")
          .getByRole("button", { name: "切换档案" }),
      ).toBeVisible();
    }

    const headingFont = await page.getByRole("heading", { level: 1, name: "人生 K 线" }).evaluate(
      (heading) => window.getComputedStyle(heading).fontFamily,
    );
    const mainFont = await page.locator("main").evaluate(
      (main) => window.getComputedStyle(main).fontFamily,
    );
    expect(headingFont).toBe(mainFont);

    await page.screenshot({
      path: testInfo.outputPath(`profile-${evidence.mode}.png`),
      fullPage: true,
    });
    releaseLoadingRequest();
    await page.unrouteAll({ behavior: "wait" });
  });
}
