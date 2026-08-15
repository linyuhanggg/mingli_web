import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function capture(page: Page, testInfo: TestInfo, name: string) {
  const directory = resolve(
    process.env.BROWSER_EVIDENCE_DIR ?? resolve(process.cwd(), "e2e/screenshots"),
    testInfo.project.name,
  );
  await mkdir(directory, { recursive: true });
  await page.screenshot({ path: resolve(directory, `${name}.png`), fullPage: true });
}

test("home task selector enters the bazi task and stays in its workbench", async ({ page }, testInfo) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { level: 1, name: "选择要解决的事" })).toBeVisible();
  await expect(page.getByRole("region", { name: "命盘" })).toBeVisible();
  await expect(page.getByRole("region", { name: "事件判断" })).toBeVisible();
  await expect(page.getByRole("region", { name: "跨术与观照" })).toBeVisible();
  await capture(page, testInfo, "home-task-selector");

  await page.locator('main a[href="/bazi"]').click();
  await expect(page).toHaveURL(/\/bazi$/);
  await expect(page.getByRole("form", { name: "八字任务输入" })).toBeVisible();
  await page.getByLabel("受测对象").fill("本人");
  await page.getByLabel("出生日期").fill("1990-05-06");
  await page.getByLabel("出生时间").fill("08:30");
  await page.getByLabel("出生地点").fill("江苏省常州市金坛区");
  await page.getByRole("button", { name: "检查输入" }).click();
  await expect(page.getByRole("heading", { name: "确认八字输入" })).toBeVisible();
  await expect(page).toHaveURL(/\/bazi$/);
  await page.getByRole("button", { name: "确认并进入工作台" }).click();
  await expect(page.getByRole("heading", { name: "八字工作台" })).toBeVisible();
  await expect(page.getByRole("status", { name: "盘面尚未生成" })).toBeVisible();
  await expect(page).toHaveURL(/\/bazi$/);
  await capture(page, testInfo, "bazi-workbench-unavailable");
});

test("bazi workbench changes from one column to two columns at the frozen desktop boundary", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "1440", "layout boundary is checked once on the wide project");

  for (const { width, expectedColumns } of [
    { width: 768, expectedColumns: 1 },
    { width: 1024, expectedColumns: 2 },
    { width: 1440, expectedColumns: 2 },
  ]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/bazi", { waitUntil: "domcontentloaded" });
    await page.getByLabel("受测对象").fill("本人");
    await page.getByLabel("出生日期").fill("1990-05-06");
    await page.getByLabel("出生时间").fill("08:30");
    await page.getByLabel("出生地点").fill("江苏省常州市金坛区");
    await page.getByRole("button", { name: "检查输入" }).click();
    await page.getByRole("button", { name: "确认并进入工作台" }).click();

    const workspace = page.locator('[data-layout="workbench-workspace"]');
    await expect(workspace).toBeVisible();
    const layout = await workspace.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        columns: style.gridTemplateColumns.trim().split(/\s+/).filter(Boolean).length,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
      };
    });

    expect(layout.columns, `${width}px workbench column count`).toBe(expectedColumns);
    expect(layout.documentWidth, `${width}px workbench overflow`).toBeLessThanOrEqual(
      layout.viewportWidth,
    );
  }
});

test("event, observation and cross-product routes keep their own inputs", async ({ page }) => {
  const cases = [
    { route: "/liuyao", form: "六爻任务输入", label: "起卦方式" },
    { route: "/qimen", form: "奇门任务输入", label: "场景侧重" },
    { route: "/daliuren", form: "大六壬任务输入", label: "判断侧重" },
    { route: "/jianxiang", form: "见相任务输入", label: "观照模式" },
    { route: "/hecan", form: "命盘合参任务输入", label: "立命资料" },
    { route: "/wenshi", form: "问事合参任务输入", label: "同一问题" },
  ] as const;

  for (const entry of cases) {
    await page.goto(entry.route, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("form", { name: entry.form })).toBeVisible();
    await expect(page.getByLabel(entry.label, { exact: true })).toBeVisible();
    await expect(page.getByText("UI 演示数据")).toHaveCount(0);
  }
});

test("canwen route redirects to hecan after the merge into 命盘合参", async ({ page }) => {
  await page.goto("/canwen", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/hecan\/?$/);
  await expect(page.getByRole("form", { name: "命盘合参任务输入" })).toBeVisible();
});

test("jianxiang keeps media local and exposes consent, delete, and confirmation boundaries", async ({ page }) => {
  await page.goto("/jianxiang", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("status", { name: "相机采集待接入" })).toBeVisible();

  await page.getByRole("checkbox", { name: /照片处理独立同意/ }).check();
  await page.getByRole("button", { name: "检查输入" }).click();
  await expect(page.getByText("请选择一张照片")).toBeVisible();
  await expect(page.locator("#jianxiang-file")).toBeFocused();

  const fileInput = page.locator("#jianxiang-file");
  const file = { name: "face.jpg", mimeType: "image/jpeg", buffer: Buffer.from("local-image") };
  await fileInput.setInputFiles(file);
  await expect(page.getByRole("status", { name: "已选择本地照片" })).toContainText("face.jpg");
  await page.getByRole("button", { name: "检查照片质量" }).click();
  await expect(page.getByRole("status", { name: "照片质量检查待接入" })).toBeVisible();

  await page.getByRole("button", { name: "删除本地照片" }).click();
  await expect(page.getByRole("status", { name: "本地照片已删除" })).toBeVisible();
  await expect(fileInput).toHaveValue("");

  await fileInput.setInputFiles(file);
  await page.getByLabel("用户补充信息").fill("左侧步态需要结合本人补充");
  await page.getByRole("checkbox", { name: /保存到见相档案/ }).check();
  await page.getByRole("button", { name: "检查输入" }).click();
  await expect(page.getByRole("heading", { name: "确认见相输入" })).toBeVisible();
  await expect(page.getByText("左侧步态需要结合本人补充")).toBeVisible();
  await expect(page.getByText("见相档案（需服务端确认）")).toBeVisible();
});

test("relationship routes expose two parties and a separate relationship area", async ({ page }, testInfo) => {
  await page.goto("/bazi/hepan", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("form", { name: "八字双人合盘输入" })).toBeVisible();
  await expect(page.getByRole("group", { name: "甲方资料" })).toBeVisible();
  await expect(page.getByRole("group", { name: "乙方资料" })).toBeVisible();
  await expect(page.getByLabel("关系类型")).toBeVisible();
  await expect(page.getByRole("heading", { name: "甲方 / 乙方 / 关系区" })).toBeVisible();
  await capture(page, testInfo, "bazi-relationship-input");
});
