import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LifeKlineRoute, { metadata } from "@/app/life-kline/page";
import {
  LifeKlinePage,
  type LifeKlineViewState,
} from "@/components/life-kline-page";
import { ApiError } from "@/lib/api";

const mockListProfiles = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  usePathname: () => "/life-kline",
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: mockListProfiles,
}));

beforeEach(() => {
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
});

afterEach(() => {
  vi.useRealTimers();
});

const stateCases: readonly [LifeKlineViewState, string][] = [
  ["need-input", "需要档案"],
  ["select-profile", "选择档案"],
  ["loading", "正在读取时间层事实"],
  ["unsupported", "数据不足，暂不支持绘制"],
  ["error", "读取失败"],
];

describe("/life-kline honest non-ready states", () => {
  it.each(stateCases)("renders %s without a ready result", (state, title) => {
    render(<LifeKlinePage initialState={state} profileOptions={[]} />);

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { level: 1, name: "人生 K 线" })).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: title })).toBeVisible();
    expect(main).toHaveAttribute("data-view-state", state);
    expect(main.querySelector('[data-state="ready"]')).toBeNull();
  });

  it("loads the real profile list and distinguishes loading from empty", async () => {
    let resolveProfiles!: (value: { profiles: [] }) => void;
    mockListProfiles.mockReturnValueOnce(
      new Promise<{ profiles: [] }>((resolvePromise) => {
        resolveProfiles = resolvePromise;
      }),
    );
    render(<LifeKlinePage />);

    fireEvent.click(screen.getByRole("button", { name: "选择已有档案" }));
    expect(screen.getByRole("heading", { level: 2, name: "正在加载档案" })).toBeVisible();
    expect(mockListProfiles).toHaveBeenCalledTimes(1);

    await act(async () => resolveProfiles({ profiles: [] }));

    expect(screen.getByRole("heading", { level: 2, name: "选择档案" })).toBeVisible();
    expect(screen.getByText("当前没有可在此页读取的档案。")).toBeVisible();
    expect(screen.getByRole("link", { name: "管理受测人档案" })).toHaveAttribute(
      "href",
      "/account/profiles",
    );
  });

  it("fails closed when profiles cannot be loaded and supports an explicit retry", async () => {
    mockListProfiles.mockRejectedValueOnce(new Error("offline"));
    render(<LifeKlinePage initialState="select-profile" />);

    expect(
      await screen.findByRole("heading", { level: 2, name: "档案读取失败" }),
    ).toBeVisible();
    expect(screen.queryByText("当前没有可在此页读取的档案。")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新加载档案" }));

    expect(await screen.findByText("当前没有可在此页读取的档案。")).toBeVisible();
    expect(mockListProfiles).toHaveBeenCalledTimes(2);
  });

  it("offers a login continuation instead of retrying an unauthorized profile load", async () => {
    mockListProfiles.mockRejectedValueOnce(new ApiError("需要登录", 401));
    render(<LifeKlinePage initialState="select-profile" />);

    expect(
      await screen.findByRole("heading", { level: 2, name: "登录后选择档案" }),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "重新加载档案" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute(
      "href",
      "/auth/login?next=%2Flife-kline%3Fstate%3Dselect-profile",
    );
  });

  it("maps a real saved profile response and resolves submission to honest unsupported", async () => {
    mockListProfiles.mockResolvedValueOnce({
      profiles: [
        {
          profile_id: "profile-a",
          profile_version_id: "profile-version-a",
          subject_ref: "profile-version:profile-version-a",
          version: 3,
          display_name: "测试档案甲",
          created_at: "2026-08-31T00:00:00Z",
        },
      ],
    });
    render(<LifeKlinePage initialState="select-profile" />);

    const profile = await screen.findByRole("radio", { name: /测试档案甲/ });
    expect(profile).toHaveAttribute("value", "profile-version-a");
    expect(screen.getByText("版本 3")).toBeVisible();

    fireEvent.click(profile);
    fireEvent.click(screen.getByRole("button", { name: "读取人生 K 线状态" }));

    expect(
      screen.getByRole("heading", { level: 2, name: "数据不足，暂不支持绘制" }),
    ).toBeVisible();
    expect(screen.getByRole("main")).toHaveAttribute("data-view-state", "unsupported");
    expect(
      screen.queryByRole("heading", { level: 2, name: "正在读取时间层事实" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/出生|生辰|profile-version-a/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "刷新状态" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "切换档案" })).toHaveLength(2);
  });

  it("discards an unconfirmed profile when selection is cancelled", () => {
    render(
      <LifeKlinePage
        initialState="select-profile"
        profileOptions={[
          { id: "profile-version-a", label: "测试档案甲", versionLabel: "版本 A" },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("radio", { name: /测试档案甲/ }));
    fireEvent.click(screen.getByRole("button", { name: "取消" }));

    expect(screen.getByRole("main")).toHaveAttribute("data-view-state", "need-input");
    expect(screen.getByRole("heading", { level: 2, name: "需要档案" })).toBeVisible();
    expect(screen.queryByLabelText("当前档案")).not.toBeInTheDocument();
  });

  it.each([
    ["without a temporary change", false],
    ["after temporarily choosing another profile", true],
  ])("restores a confirmed profile when switching is cancelled %s", (_label, chooseAnother) => {
    render(
      <LifeKlinePage
        initialState="select-profile"
        profileOptions={[
          { id: "profile-version-a", label: "测试档案甲", versionLabel: "版本 A" },
          { id: "profile-version-b", label: "测试档案乙", versionLabel: "版本 B" },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("radio", { name: /测试档案甲/ }));
    fireEvent.click(screen.getByRole("button", { name: "读取人生 K 线状态" }));
    fireEvent.click(screen.getAllByRole("button", { name: "切换档案" })[0]);

    if (chooseAnother) {
      fireEvent.click(screen.getByRole("radio", { name: /测试档案乙/ }));
    }

    expect(within(screen.getByLabelText("当前档案")).getByText("测试档案甲")).toBeVisible();
    expect(within(screen.getByLabelText("当前档案")).queryByText("测试档案乙")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "取消" }));

    expect(screen.getByRole("main")).toHaveAttribute("data-view-state", "unsupported");
    expect(
      screen.getByRole("heading", { level: 2, name: "数据不足，暂不支持绘制" }),
    ).toBeVisible();
    expect(within(screen.getByLabelText("当前档案")).getByText("测试档案甲")).toBeVisible();
    expect(screen.queryByText("测试档案乙")).not.toBeInTheDocument();
    expect(mockListProfiles).not.toHaveBeenCalled();
  });

  it("keeps unsupported unavailable while omitting an inaccurate breadcrumb badge", () => {
    render(<LifeKlinePage initialState="unsupported" profileOptions={[]} />);

    expect(
      screen.getByRole("status", { name: "数据不足，暂不支持绘制" }),
    ).toHaveAttribute("data-state", "unavailable");
    expect(
      screen.getByRole("navigation", { name: "面包屑" }).querySelector("[data-state]"),
    ).toBeNull();
  });

  it("accepts a supplied opaque profile choice without starting a request that must time out", () => {
    render(
      <LifeKlinePage
        initialState="select-profile"
        profileOptions={[
          { id: "profile-version-a", label: "测试档案甲", versionLabel: "版本 A" },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("radio", { name: /测试档案甲/ }));
    fireEvent.click(screen.getByRole("button", { name: "读取人生 K 线状态" }));

    expect(
      screen.getByRole("heading", { level: 2, name: "数据不足，暂不支持绘制" }),
    ).toBeVisible();
    expect(screen.queryByText(/出生|生辰/)).not.toBeInTheDocument();
  });

  it("delays the local loading placeholder, later enables cancel, and stops at the timeout", () => {
    vi.useFakeTimers();
    render(<LifeKlinePage initialState="loading" />);

    expect(screen.queryByTestId("life-kline-loading-placeholder")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "取消读取" })).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(299));
    expect(screen.queryByTestId("life-kline-loading-placeholder")).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByTestId("life-kline-loading-placeholder")).toBeVisible();

    act(() => vi.advanceTimersByTime(14_700));
    expect(screen.getByRole("button", { name: "取消读取" })).toBeVisible();

    act(() => vi.advanceTimersByTime(45_000));
    expect(screen.getByRole("heading", { level: 2, name: "读取超时" })).toBeVisible();
    expect(screen.getByText(/等待已停止。请返回/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
  });

  it("fails closed for unknown route states", async () => {
    const page = await LifeKlineRoute({
      searchParams: Promise.resolve({ state: "future-ready-state" }),
    });
    render(page);

    expect(screen.getByRole("heading", { level: 2, name: "需要档案" })).toBeVisible();
    expect(screen.queryByText("future-ready-state")).not.toBeInTheDocument();
  });

  it("uses public metadata without claiming a generated result", () => {
    expect(metadata.title).toBe("人生 K 线");
    expect(metadata.description).toContain("权威事实");
    expect(metadata.description).toContain("暂不绘制");
  });

  it("keeps the implementation free of generated scores, chart code, and browser calculation", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/components/life-kline-page.tsx"),
      "utf8",
    );

    expect(source).not.toMatch(/Math\.random|fixture|0\s*[–-]\s*100/i);
    expect(source).not.toMatch(/life-kline-chart|open\s*[,/:]|high\s*[,/:]|low\s*[,/:]|close\s*[,/:]/i);
    expect(source).not.toMatch(/干支.*计算|五行.*计算|命理.*计算/);
  });

  it("keeps ordinary public headings on the inherited UI sans family", () => {
    const lifeKlineStyles = readFileSync(
      resolve(process.cwd(), "src/components/life-kline-page.module.css"),
      "utf8",
    );
    const retiredStyles = readFileSync(
      resolve(process.cwd(), "src/components/retired-public-surface.module.css"),
      "utf8",
    );

    expect(lifeKlineStyles).not.toContain("font-family: var(--ds-font-domain)");
    expect(retiredStyles).not.toContain("font-family: var(--ds-font-domain)");
  });
});
