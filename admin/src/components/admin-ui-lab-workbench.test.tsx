import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AdminUiLabWorkbench } from "@/components/admin-ui-lab-workbench";

describe("AdminUiLabWorkbench", () => {
  it("keeps the demo marker and route/state/viewport/role selectors discoverable", async () => {
    const user = userEvent.setup();
    render(<AdminUiLabWorkbench />);

    expect(document.querySelector('[data-ui-lab-ready="true"]')).toBeInTheDocument();
    expect(screen.getByText("UI 演示数据")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "演示路由" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "页面状态" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "预览视口" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "员工角色" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "能力状态" })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "写操作状态" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "演示路由" }), "/refunds");
    expect(screen.getByRole("table", { name: "退款列表" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "预览视口" }), "360");
    expect(screen.getByText("当前业务内层预览：360px")).toBeVisible();
    expect(document.querySelector('[data-preview-viewport="360"]')).toHaveAttribute(
      "data-preview-scope",
      "business-surface",
    );
  });
});
