import { render, screen, waitFor, within } from "@testing-library/react";
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
  listProfiles: vi.fn(),
  listReadings: vi.fn(),
}));

vi.mock("@/lib/api", () => api);


beforeEach(() => {
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.listReadings.mockReset();
  api.listReadings.mockResolvedValue({ readings: [] });
});


describe("private P0 surfaces", () => {
  it("keeps today and seven-day content empty until a real profile exists", () => {
    render(<AppPage />);

    expect(screen.getByRole("button", { name: "今日" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "今天还没有可读摘要" })).toBeVisible();
    expect(screen.getByText(/不会用示例运势占据真实结果的位置/)).toBeVisible();
  });

  it("explains immutable profile versions and offers a real next step", async () => {
    render(<ProfilesPage />);

    expect(
      screen.getByText(/每次修改都会形成新的不可变档案版本/),
    ).toBeVisible();
    await waitFor(() => {
      expect(
        screen.getByRole("status", { name: "还没有已保存的档案" }),
      ).toBeVisible();
      expect(
        screen.getByRole("link", { name: "开始建立档案" }),
      ).toHaveAttribute("href", "/app/profile/new");
    });
  });

  it("shows only server-returned reading statuses on the history list", async () => {
    api.listReadings.mockResolvedValue({
      readings: [
        {
          reading_version_id: "33333333-3333-4333-8333-333333333333",
          reading_root_id: "44444444-4444-4444-8444-444444444444",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          capability_id: "fortune",
          version: 1,
          status: "accepted",
          object_id: "near_time_personal",
          dimension_ids: ["overview"],
          horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
          prior_answer: null,
          input_request: null,
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });
    render(<ReadingsPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: /日运与周运/ }),
      ).toHaveAttribute(
        "href",
        "/app/readings/33333333-3333-4333-8333-333333333333",
      );
    });
    expect(screen.getByText("已交付")).toBeVisible();
    expect(screen.queryByText("准备解读")).not.toBeInTheDocument();
  });

  it("keeps the empty readings list honest with a real next step", async () => {
    render(<ReadingsPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("status", { name: "还没有可显示的解读" }),
      ).toBeVisible();
    });
    expect(screen.getByText(/最近 50 条解读版本/)).toBeVisible();
    expect(screen.getByRole("link", { name: "发起解读" })).toHaveAttribute(
      "href",
      "/app",
    );
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
    expect(within(mobileNavigation).getByRole("link", { name: "首页" })).not.toHaveAttribute("aria-current");
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
