import { render, screen, within } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import AppPage from "@/app/app/page";
import LiuyaoPage from "@/app/app/ask/liuyao/page";
import NewProfilePage from "@/app/app/profile/new/page";
import ProfilesPage from "@/app/app/profiles/page";
import ReadingsPage from "@/app/app/readings/page";
import { PrivateShell } from "@/components/private-shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/readings/demo-reading",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const api = vi.hoisted(() => ({
  getCsrfToken: vi.fn(),
}));

vi.mock("@/lib/api", () => api);


beforeEach(() => {
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
});


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

  it("shows the real server-driven reading status legend without fabricated states", () => {
    render(<ReadingsPage />);

    for (const label of ["等待输入", "准备解读", "事实已准备", "正在接纳正文", "已交付", "已停止"]) {
      expect(screen.getByText(label)).toBeVisible();
    }
    expect(screen.getByRole("heading", { name: "状态由服务端返回，本页不代为生成" })).toBeVisible();
  });

  it("keeps the readings list as an explicit placeholder with a real next step", () => {
    render(<ReadingsPage />);

    expect(screen.getByRole("heading", { name: "目前没有可显示的真实解读" })).toBeVisible();
    expect(screen.getByText(/暂无可列举的解读历史接口/)).toBeVisible();
    expect(screen.getByText(/reading_version_id/)).toBeVisible();
    expect(screen.getByText(/不会伪造任何报告/)).toBeVisible();
    expect(screen.getByRole("link", { name: "发起解读" })).toHaveAttribute("href", "/app");
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

  it("keeps a single page title on the new profile surface and exposes the form title as h2", () => {
    render(<NewProfilePage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "建立命理档案" })).toBeVisible();
  });

  it("keeps a single page title on the liuyao surface and exposes the form title as h2", () => {
    render(<LiuyaoPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "一事一问 · 六爻" })).toBeVisible();
  });
});
