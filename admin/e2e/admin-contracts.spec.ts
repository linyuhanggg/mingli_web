import { expect, test } from "@playwright/test";

test("Admin route families render distinct honest surfaces", async ({ page }) => {
  const cases = [
    ["/users/demo-user", "用户详情字段", "身份平台暂不可用"],
    ["/runtime", "运行时控制面", "Runtime 平台暂不可用"],
    ["/health", "健康检查面", "依赖未就绪"],
    ["/settings", "系统设置面", "系统设置暂不可用"],
  ] as const;

  for (const [route, heading, status] of cases) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.getByRole("table")).toHaveCount(0);
    await expect(page.getByRole("status", { name: status })).toBeVisible();
  }
});

test("representative list families expose domain-specific columns", async ({ page }) => {
  const cases = [
    ["/users", ["身份", "会话", "同意"]],
    ["/payments", ["支付尝试", "订单", "渠道", "到账事实"]],
    ["/staff", ["员工", "角色", "会话"]],
    ["/readings", ["任务根", "版本", "阶段", "受测对象"]],
    ["/cms/pages", ["内容", "版本", "发布态"]],
  ] as const;

  for (const [route, headers] of cases) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    for (const header of headers) {
      const columnHeader = page.getByRole("columnheader", {
        name: header,
        exact: true,
        includeHidden: true,
      });
      await expect(columnHeader).toHaveCount(1);
      if (page.viewportSize()?.width === 1440) {
        await expect(columnHeader).toBeVisible();
      }
    }
  }
});
