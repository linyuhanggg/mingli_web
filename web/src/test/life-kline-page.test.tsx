import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import LifeKlineRoute, { metadata } from "@/app/life-kline/page";
import {
  LifeKlinePage,
  type LifeKlineViewState,
} from "@/components/life-kline-page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/life-kline",
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

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
    render(<LifeKlinePage initialState={state} />);

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { level: 1, name: "人生 K 线" })).toBeVisible();
    expect(within(main).getByRole("heading", { level: 2, name: title })).toBeVisible();
    expect(main).toHaveAttribute("data-view-state", state);
    expect(main.querySelector('[data-state="ready"]')).toBeNull();
  });

  it("moves from need-input to an honest empty profile picker", () => {
    render(<LifeKlinePage />);

    fireEvent.click(screen.getByRole("button", { name: "选择已有档案" }));
    expect(screen.getByRole("heading", { level: 2, name: "选择档案" })).toBeVisible();
    expect(screen.getByText("当前没有可在此页读取的档案。")).toBeVisible();
    expect(screen.getByRole("link", { name: "管理受测人档案" })).toHaveAttribute(
      "href",
      "/account/profiles",
    );
  });

  it("accepts a supplied opaque profile choice and enters loading without exposing birth data", () => {
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

    expect(screen.getByRole("heading", { level: 2, name: "正在读取时间层事实" })).toBeVisible();
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
    expect(screen.getByRole("button", { name: "重试" })).toBeVisible();
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
});
