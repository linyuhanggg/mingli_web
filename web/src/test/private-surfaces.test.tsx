import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";

import { AccountSessionProvider } from "@/components/account-session-context";
import { DashboardHub as AppPage } from "@/components/dashboard-hub";
import { PrivateShell } from "@/components/private-shell";
import { ProfileArchive as ProfilesPage } from "@/components/profile-archive";
import { ReadingHistory as ReadingsPage } from "@/components/reading-history";
import { ApiError } from "@/lib/api";

const navigationState = vi.hoisted(() => ({
  pathname: "/account/history/demo-reading",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  getReadingResult: vi.fn(),
  listProfiles: vi.fn(),
  listReadings: vi.fn(),
  startPreviewReading: vi.fn(),
  formatProfileOption: (profile: { version: number; created_at: string }) =>
    `档案 ${profile.version}`,
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...api,
}));


beforeEach(() => {
  navigationState.pathname = "/account/history/demo-reading";
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
  api.getReadingResult.mockReset();
  api.getReadingResult.mockResolvedValue({ verification: null });
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.listReadings.mockReset();
  api.listReadings.mockResolvedValue({ readings: [] });
});


describe("private P0 surfaces", () => {
  it("loads real dashboard data and gives an honest empty-profile next step", async () => {
    render(<AppPage />);

    expect(
      screen.getByRole("status", { name: "正在整理你的私人首页" }),
    ).toBeVisible();

    expect(
      await screen.findByRole("status", { name: "先建立第一份命理档案" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "建立第一份档案" })).toHaveAttribute(
      "href",
      "/app/profile/new",
    );
    expect(
      screen.getByRole("link", { name: "不建档，直接一事一问" }),
    ).toHaveAttribute("href", "/app/ask/liuyao");
    expect(screen.queryByText(/Runtime|模型未接通/)).not.toBeInTheDocument();
  });

  it("links today and week choices to real flows and surfaces processing work", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 2,
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });
    api.listReadings.mockResolvedValue({
      readings: [
        {
          reading_version_id: "33333333-3333-4333-8333-333333333333",
          reading_root_id: "44444444-4444-4444-8444-444444444444",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          capability_id: "fortune",
          version: 1,
          status: "completing",
          object_id: "near_time_personal",
          dimension_ids: ["overview"],
          horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
          prior_answer: null,
          input_request: null,
          created_at: "2026-08-10T02:00:00Z",
        },
      ],
    });

    render(<AppPage />);

    expect(
      await screen.findByRole("heading", { name: "有 1 条解读正在处理中" }),
    ).toBeVisible();
    expect(screen.getByText(/最新档案 v2/)).toBeVisible();
    expect(screen.getByRole("link", { name: "查看今日" })).toHaveAttribute(
      "href",
      "/app/fortune/today",
    );
    expect(screen.getByRole("link", { name: "查看近七日" })).toHaveAttribute(
      "href",
      "/app/fortune/week",
    );
    expect(
      screen.getByRole("link", { name: "继续查看处理进度" }),
    ).toHaveAttribute(
      "href",
      "/app/readings/33333333-3333-4333-8333-333333333333",
    );
  });

  it("offers the latest delivered reading as a concrete continuation", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 1,
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });
    api.listReadings.mockResolvedValue({
      readings: [
        {
          reading_version_id: "55555555-5555-4555-8555-555555555555",
          reading_root_id: "66666666-6666-4666-8666-666666666666",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          capability_id: "bazi",
          version: 3,
          status: "accepted",
          object_id: "personal_chart",
          dimension_ids: ["overview"],
          horizon: { kind_id: "natal", start: null, end: null },
          prior_answer: null,
          input_request: null,
          created_at: "2026-08-10T03:00:00Z",
        },
      ],
    });

    render(<AppPage />);

    expect(
      await screen.findByRole("heading", { name: "最近一条解读待你核对" }),
    ).toBeVisible();
    expect(api.getReadingResult).toHaveBeenCalledWith(
      "55555555-5555-4555-8555-555555555555",
    );
    expect(
      screen.getByRole("link", { name: "打开并完成核对" }),
    ).toHaveAttribute(
      "href",
      "/app/readings/55555555-5555-4555-8555-555555555555",
    );
  });

  it("surfaces a standalone liuyao verification even when no profile exists", async () => {
    api.listReadings.mockResolvedValue({
      readings: [
        {
          reading_version_id: "77777777-7777-4777-8777-777777777777",
          reading_root_id: "88888888-8888-4888-8888-888888888888",
          profile_version_id: null,
          capability_id: "liuyao",
          version: 1,
          status: "accepted",
          object_id: "concrete_event",
          dimension_ids: ["career"],
          horizon: { kind_id: "instant", start: null, end: null },
          prior_answer: null,
          input_request: null,
          created_at: "2026-08-10T04:00:00Z",
        },
      ],
    });

    render(<AppPage />);

    expect(
      await screen.findByRole("heading", { name: "最近一条解读待你核对" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "打开并完成核对" }),
    ).toHaveAttribute(
      "href",
      "/app/readings/77777777-7777-4777-8777-777777777777",
    );
    expect(
      screen.queryByRole("status", { name: "先建立第一份命理档案" }),
    ).not.toBeInTheDocument();
  });

  it("recovers from a guest dashboard request failure", async () => {
    const user = userEvent.setup();
    api.listProfiles
      .mockRejectedValueOnce(new Error("网络暂时不可用"))
      .mockResolvedValueOnce({ profiles: [] });
    api.listReadings
      .mockRejectedValueOnce(new Error("网络暂时不可用"))
      .mockResolvedValueOnce({ readings: [] });

    render(<AppPage />);

    expect(
      await screen.findByRole("alert", { name: "私人首页暂时无法更新" }),
    ).toBeVisible();
    expect(screen.getByText(/游客会话/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "重新载入私人首页" }));

    expect(
      await screen.findByRole("status", { name: "先建立第一份命理档案" }),
    ).toBeVisible();
    expect(api.listProfiles).toHaveBeenCalledTimes(2);
    expect(api.listReadings).toHaveBeenCalledTimes(2);
  });

  it("does not give guest-session recovery copy to a signed-in dashboard failure", async () => {
    api.getAccount.mockResolvedValue({
      user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
      identities: [
        {
          id: "8d2f1a4b-6c3e-4d9f-8a5b-2e7c4f1d9a3b",
          provider: "email",
          masked_destination: "q***@example.com",
          verified_at: "2026-08-01T00:00:00Z",
        },
      ],
    });
    api.listProfiles.mockRejectedValue(new Error("网络暂时不可用"));
    api.listReadings.mockRejectedValue(new Error("网络暂时不可用"));

    render(
      <AccountSessionProvider>
        <AppPage />
      </AccountSessionProvider>,
    );

    expect(
      await screen.findByRole("alert", { name: "私人首页暂时无法更新" }),
    ).toBeVisible();
    expect(await screen.findByText(/已登录设备的资料读取失败/)).toBeVisible();
    expect(screen.queryByText(/游客会话偶尔会/)).not.toBeInTheDocument();
  });

  it("explains immutable profile versions and offers a real next step", async () => {
    render(<ProfilesPage />);

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
        "/account/history/33333333-3333-4333-8333-333333333333",
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
    expect(within(desktopNavigation).getByRole("link", { name: "推演历史", hidden: true })).toHaveAttribute("href", "/account/history");
    expect(within(mobileNavigation).getAllByRole("link")).toHaveLength(5);
    expect(within(mobileNavigation).getByRole("link", { name: "历史" })).toHaveAttribute("href", "/account/history");
    expect(within(desktopNavigation).getByRole("link", { name: "推演历史", hidden: true })).toHaveAttribute("aria-current", "page");
    expect(within(mobileNavigation).getByRole("link", { name: "历史" })).toHaveAttribute("aria-current", "page");
    expect(within(mobileNavigation).getByRole("link", { name: "我的" })).not.toHaveAttribute("aria-current");
  });

  it("moves keyboard focus to the private main region after a client route change", async () => {
    navigationState.pathname = "/account";
    const { rerender } = render(
      <PrivateShell>
        <p>首页内容</p>
      </PrivateShell>,
    );
    const main = screen.getByRole("main");
    expect(main).not.toHaveFocus();

    navigationState.pathname = "/account/profiles";
    rerender(
      <PrivateShell>
        <p>档案内容</p>
      </PrivateShell>,
    );

    await waitFor(() => {
      expect(main).toHaveFocus();
    });
  });

});
