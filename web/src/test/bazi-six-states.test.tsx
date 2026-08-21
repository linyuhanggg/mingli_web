import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { UiLab } from "@/components/ui-lab/ui-lab";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import { getProductDefinition } from "@/products/catalog";

afterEach(cleanup);

function renderLab() {
  return render(<UiLab demoLabel="UI 演示数据" />);
}

async function chooseRoute(id: string) {
  const user = userEvent.setup();
  renderLab();
  await user.selectOptions(screen.getByRole("combobox", { name: "页面与场景" }), id);
  return user;
}

describe("bazi result and workbench six states", () => {
  it("keeps fake workbench promises marked 待接入 and clickable", () => {
    render(
      <WorkbenchShell
        onBack={() => undefined}
        product={getProductDefinition("bazi")}
      />,
    );

    expect(screen.getByText("待接入 ·", { exact: false })).toBeVisible();
    expect(screen.getByRole("button", { name: /返回确认/ })).toBeEnabled();
    expect(screen.getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");
    expect(screen.getByRole("button", { name: "导出待接入" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /时间层待接入/ })).toBeDisabled();
  });

  it("reaches honest clickable workbench states from UI Lab", async () => {
    const user = await chooseRoute("workbench-handle");
    const preview = () => within(screen.getByTestId("ui-lab-preview"));

    expect(preview().getByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(preview().getByRole("heading", { name: "阅读与报告" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "loading");
    expect(preview().getByRole("status", { name: "正在载入工作台" })).toHaveAttribute(
      "data-state",
      "loading",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "empty");
    expect(preview().getByRole("status", { name: "还没有可展示的盘面" })).toHaveAttribute(
      "data-state",
      "empty",
    );
    expect(preview().getByRole("button", { name: "返回录入" })).toBeEnabled();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "failed");
    expect(preview().getByRole("alert", { name: "读取失败，请重试" })).toHaveAttribute(
      "data-state",
      "error",
    );
    expect(preview().getByRole("button", { name: "返回录入" })).toBeEnabled();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "queued");
    expect(preview().getByRole("status", { name: "盘面处理中" })).toHaveAttribute(
      "data-state",
      "processing",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unavailable");
    expect(preview().getByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(preview().getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unauthorized");
    expect(preview().getByRole("status", { name: "需要登录才能看这份结果" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );
    expect(preview().getByRole("link", { name: "登录后继续" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
  });

  it("reaches honest clickable bazi-result six states from UI Lab", async () => {
    const user = await chooseRoute("bazi-result-evidence");
    const preview = () => within(screen.getByTestId("ui-lab-preview"));

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "free-summary");
    expect(preview().getByRole("heading", { name: "八字结果页验收切片" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "loading");
    expect(preview().getByRole("status", { name: "加载中" })).toHaveAttribute("data-state", "loading");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "empty");
    expect(preview().getByRole("status", { name: "暂无内容" })).toHaveAttribute("data-state", "empty");
    expect(preview().getByRole("link", { name: "返回八字录入" })).toHaveAttribute("href", "/bazi");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "failed");
    expect(preview().getByRole("alert", { name: "处理失败" })).toHaveAttribute("data-state", "error");
    expect(preview().getByRole("link", { name: "返回八字录入" })).toHaveAttribute("href", "/bazi");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "generating");
    expect(preview().getByRole("status", { name: "生成解读" })).toHaveAttribute(
      "data-state",
      "processing",
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unavailable");
    expect(preview().getByRole("status", { name: "暂不可用" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(preview().getByText(/待接入/)).toBeVisible();
    expect(preview().getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "unauthorized");
    expect(preview().getByRole("status", { name: "登录已失效" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );
    expect(preview().getByRole("link", { name: "登录后继续" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
  });
});
