import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { UiLab } from "@/components/ui-lab/ui-lab";
import { UI_LAB_STATES } from "@/lib/ui-lab-contract";

afterEach(cleanup);

function renderLab() {
  render(<UiLab demoLabel="UI 演示数据" />);
}

async function chooseRoute(routeId: string) {
  renderLab();
  const user = userEvent.setup();
  await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), routeId);
  return user;
}

describe("Web UI Lab interactions", () => {
  it("renders a permanent boundary, complete controls, and separate completion facts", () => {
    renderLab();

    expect(screen.getByRole("heading", { level: 1, name: "Web UI Lab" })).toBeVisible();
    expect(screen.getByText("UI 演示数据")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "页面与场景" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "状态" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "查看身份" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "能力阶段" })).toBeVisible();
    expect(screen.getByRole("group", { name: "预览宽度" })).toBeVisible();
    expect(screen.getByText("UI 完成度")).toBeVisible();
    expect(screen.getByText("算法接入度")).toBeVisible();
    expect(screen.getByRole("heading", { name: "预览：八字任务录入" })).toBeVisible();
    expect(screen.getByText("bazi-chart/v1")).toBeVisible();

    const stateSelect = screen.getByRole("combobox", { name: "状态" });
    expect(within(stateSelect).getAllByRole("option")).toHaveLength(UI_LAB_STATES.length);
  });

  it("makes every frozen route pattern discoverable and clickable", async () => {
    const user = userEvent.setup();
    renderLab();

    const routeButtons = screen.getAllByRole("button", { name: /^预览路由 / });
    expect(routeButtons).toHaveLength(56);

    await user.click(screen.getByRole("button", { name: "预览路由 /auth/register" }));
    expect(screen.getByRole("heading", { name: "注册" })).toBeVisible();
    expect(screen.getByText("auth-surface/v1")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "预览路由 /tools/name" }));
    expect(screen.getByRole("heading", { name: "姓名分析" })).toBeVisible();
  });

  it("applies route, state, role, capability, and viewport controls to the preview", async () => {
    const user = userEvent.setup();
    renderLab();

    await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), "account-history-detail");
    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "payment-failed");
    await user.selectOptions(screen.getByRole("combobox", { name: "查看身份" }), "member");
    await user.selectOptions(screen.getByRole("combobox", { name: "能力阶段" }), "paused");
    await user.click(screen.getByRole("button", { name: "768 像素" }));

    expect(screen.getByRole("heading", { name: "预览：历史报告阅读" })).toBeVisible();
    const preview = within(screen.getByTestId("ui-lab-preview"));
    expect(preview.getByText("支付失败")).toBeVisible();
    expect(preview.getByText("登录用户")).toBeVisible();
    expect(preview.getByText("历史可读")).toBeVisible();
    expect(preview.getByText("暂停新任务")).toBeVisible();
    expect(screen.getByTestId("ui-lab-preview")).toHaveAttribute("data-viewport", "768");
    expect(screen.getByTestId("ui-lab-preview")).toHaveStyle({ width: "768px" });
  });

  it("uses the production task input form for product routes", async () => {
    const user = userEvent.setup();
    renderLab();

    expect(screen.getByRole("form", { name: "八字任务输入" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));

    expect(screen.getByRole("heading", { name: "请先修正以下输入" })).toBeVisible();
    expect(screen.getByRole("group", { name: /出生日期/ })).toHaveFocus();
  });

  it("fills the production product form when the filled state is selected", async () => {
    const user = userEvent.setup();
    renderLab();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "filled");

    expect(screen.getByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.getByLabelText("受测对象")).toHaveValue("演示受测人");
    expect(screen.getByLabelText("出生年份")).toHaveValue("1992");
    expect(screen.getByLabelText("出生月份")).toHaveValue("06");
    expect(screen.getByLabelText("出生日期")).toHaveValue("18");
    expect(screen.getByLabelText("出生小时")).toHaveValue("08");
    expect(screen.getByLabelText("出生分钟")).toHaveValue("30");
  });

  it("blocks non-test identities from an internal-test capability", async () => {
    const user = userEvent.setup();
    renderLab();

    await user.selectOptions(screen.getByRole("combobox", { name: "查看身份" }), "member");
    await user.selectOptions(screen.getByRole("combobox", { name: "能力阶段" }), "internal-test");

    expect(screen.getByRole("status", { name: "仅授权测试账号可用" })).toBeVisible();
    expect(screen.queryByRole("form", { name: "八字任务输入" })).not.toBeInTheDocument();
  });

  it("uses production workbench and reading shells for task recovery", async () => {
    await chooseRoute("workbench-handle");

    expect(screen.getByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "阅读与报告" })).toBeVisible();
  });

  it("uses formal Status for hepan routes without nesting a full production page", async () => {
    await chooseRoute("bazi-hepan");

    const body = screen.getByTestId("ui-lab-preview-body");
    expect(within(body).getByText("八字合盘暂无结果 Fixture")).toBeVisible();
    expect(within(body).queryByRole("main")).not.toBeInTheDocument();
    expect(screen.getByText("bazi-relationship/v1")).toBeVisible();
  });

  it("does not keep the registry unavailable title when a hepan state is changed", async () => {
    const user = await chooseRoute("bazi-hepan");
    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "ready");

    const body = screen.getByTestId("ui-lab-preview-body");
    expect(within(body).getByText("已就绪")).toBeVisible();
    expect(within(body).queryByText("八字合盘暂无结果 Fixture")).not.toBeInTheDocument();
  });

  it("exposes the frozen jianxiang capture and media lifecycle states", async () => {
    const user = await chooseRoute("jianxiang-input");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "photo-quality-failed");
    expect(screen.getByRole("alert", { name: "照片质量不合格" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "source-expired-result-ready");
    expect(screen.getByRole("status", { name: "原图已过期，结果可查看" })).toBeVisible();
  });

  it("uses the production account, auth, commerce, and public content surfaces", async () => {
    const user = await chooseRoute("account-profiles");
    expect(screen.getByRole("heading", { name: "受测人档案" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), "auth-login");
    expect(screen.getByRole("form", { name: "登录表单" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), "checkout-order");
    expect(screen.getByRole("heading", { name: "订单", level: 1 })).toBeVisible();
    expect(screen.getByText("没有服务端订单快照就不展示金额")).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), "public-library");
    expect(screen.getByRole("heading", { name: "公开内容会标明来源、整理方式和更新时间。" })).toBeVisible();
  });

  it("uses one main landmark and a shared Status for the filled auth state", async () => {
    const user = await chooseRoute("auth-login");
    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "filled");

    expect(screen.getAllByRole("main")).toHaveLength(1);
    const body = screen.getByTestId("ui-lab-preview-body");
    expect(within(body).getByText("已填写")).toBeVisible();
    expect(within(body).queryByRole("form", { name: "登录表单" })).not.toBeInTheDocument();
  });

  it.each([
    ["ready", "success", "已就绪"],
    ["free-summary", "success", "免费摘要"],
    ["loading", "loading", "加载中"],
    ["unauthorized", "unauthorized", "登录已失效"],
    ["failed", "error", "处理失败"],
  ] as const)("replaces the normal body with formal Status for %s", async (labState, statusState, title) => {
    const user = userEvent.setup();
    renderLab();
    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), labState);

    const body = screen.getByTestId("ui-lab-preview-body");
    expect(within(body).getByText(title)).toBeVisible();
    expect(body.querySelector(`[data-state="${statusState}"]`)).not.toBeNull();
    expect(within(body).queryByRole("form", { name: "八字任务输入" })).not.toBeInTheDocument();
  });
});
