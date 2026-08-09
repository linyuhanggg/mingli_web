import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import AppPage from "@/app/app/page";
import ProfilesPage from "@/app/app/profiles/page";
import ReadingDetailPage from "@/app/app/readings/[id]/page";
import ReadingsPage from "@/app/app/readings/page";
import { PrivateShell } from "@/components/private-shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/readings/demo-reading",
}));


describe("private P0 surfaces", () => {
  it("keeps today and seven-day content empty until a real profile exists", () => {
    render(<AppPage />);

    expect(screen.getByRole("button", { name: "今日" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "今天还没有可读摘要" })).toBeVisible();
    expect(screen.getByText(/不会用示例运势占据真实结果的位置/)).toBeVisible();
  });

  it("explains immutable profile versions and offers a real next step", () => {
    render(<ProfilesPage />);

    expect(screen.getByRole("heading", { name: "还没有已保存的受测档案" })).toBeVisible();
    expect(screen.getByRole("link", { name: "开始建立档案" })).toHaveAttribute("href", "/app/profile/new");
    expect(screen.getByText(/不可变档案版本/)).toBeVisible();
  });

  it("separates payment, generation, failure, and final delivery states", () => {
    render(<ReadingsPage />);

    for (const label of ["待付款", "正在确认付款", "生成与校验中", "暂时未完成", "已交付"]) {
      expect(screen.getByText(label)).toBeVisible();
    }
    expect(screen.getByText(/Accepted Copy.*Fulfillment/)).toBeVisible();
  });

  it("renders the conclusion-evidence-boundary-verification reading order as a demo", () => {
    render(<ReadingDetailPage />);

    const article = screen.getByRole("article");
    for (const label of ["先给结论", "再说明成立原因", "边界与不确定性", "三条现实核对"]) {
      expect(within(article).getByRole("heading", { name: label })).toBeVisible();
    }
    expect(screen.getByText(/零命中保持零/)).toBeVisible();
    expect(screen.getByText(/非真实交付/)).toBeVisible();
  });

  it("provides five-item desktop and mobile application navigation", () => {
    render(<PrivateShell><p>内容</p></PrivateShell>);

    const desktopNavigation = screen.getByRole("navigation", { name: "私人应用导航", hidden: true });
    const mobileNavigation = screen.getByRole("navigation", { name: "移动应用导航" });

    expect(within(desktopNavigation).getAllByRole("link", { hidden: true })).toHaveLength(5);
    expect(within(desktopNavigation).getByRole("link", { name: "解读", hidden: true })).toHaveAttribute("href", "/app/readings");
    expect(within(mobileNavigation).getAllByRole("link")).toHaveLength(5);
    expect(within(mobileNavigation).getByRole("link", { name: "解读" })).toHaveAttribute("href", "/app/readings");
    expect(within(desktopNavigation).getByRole("link", { name: "解读", hidden: true })).toHaveAttribute("aria-current", "page");
    expect(within(mobileNavigation).getByRole("link", { name: "解读" })).toHaveAttribute("aria-current", "page");
    expect(within(mobileNavigation).getByRole("link", { name: "今日" })).not.toHaveAttribute("aria-current");
  });
});
