import { render, screen, within } from "@testing-library/react";

import { StatusPanel, type StatusPanelState } from "@/components/status-panel";


const statusCases: Array<{
  state: StatusPanelState;
  title: string;
  role: "alert" | "status";
  busy: boolean;
}> = [
  { state: "loading", title: "正在同步出盘", role: "status", busy: true },
  { state: "empty", title: "还没有内容", role: "status", busy: false },
  { state: "ready", title: "盘面已就绪", role: "status", busy: false },
  { state: "locked", title: "深读暂未解锁", role: "status", busy: false },
  { state: "need-input", title: "需要补充信息", role: "status", busy: false },
  { state: "error", title: "暂时无法完成", role: "alert", busy: false },
  { state: "processing", title: "正在处理中", role: "status", busy: true },
  { state: "success", title: "已经完成", role: "status", busy: false },
  { state: "disabled", title: "暂不可用", role: "status", busy: false },
];

describe("StatusPanel", () => {
  it.each(statusCases)(
    "renders the $state state with the correct live-region semantics",
    ({ state, title, role, busy }) => {
      const { container } = render(<StatusPanel state={state} />);
      const panel = screen.getByRole(role);

      expect(panel).toHaveAttribute("data-state", state);
      expect(within(panel).getByRole("heading", { level: 2, name: title })).toBeVisible();
      expect(panel).toHaveAttribute("aria-atomic", "true");

      if (busy) {
        expect(panel).toHaveAttribute("aria-busy", "true");
      } else {
        expect(panel).not.toHaveAttribute("aria-busy");
      }

      expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    },
  );

  it("uses custom copy and renders a native action link when both action fields exist", () => {
    render(
      <StatusPanel
        actionHref="/app/profile/new"
        actionLabel="补全资料"
        description="还缺出生时间，请先补全后继续。"
        state="empty"
        title="资料尚未完整"
      />,
    );

    const panel = screen.getByRole("status", { name: "资料尚未完整" });

    expect(within(panel).getByText("还缺出生时间，请先补全后继续。")).toBeVisible();
    expect(within(panel).getByRole("link", { name: "补全资料" })).toHaveAttribute(
      "href",
      "/app/profile/new",
    );
  });

  it("keeps the action absent unless it has both an href and an accessible label", () => {
    render(<StatusPanel actionHref="/support" state="error" />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("explains why the default disabled state cannot be used", () => {
    render(<StatusPanel state="disabled" />);

    expect(screen.getByText(/当前所需条件尚未满足/)).toBeVisible();
  });

  it("keeps locked content scoped to deep reading while chart facts remain available", () => {
    render(<StatusPanel state="locked" />);

    expect(screen.getByText(/免费盘面事实仍可查看/)).toBeVisible();
    expect(screen.getByText(/深读或付费时间层/)).toBeVisible();
  });
});
