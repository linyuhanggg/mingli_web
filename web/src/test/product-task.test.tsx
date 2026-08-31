import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import { ProductTaskPage } from "@/components/task/product-task-page";
import { ApiError, listProfiles } from "@/lib/api";
import { PRODUCT_CATALOG } from "@/products/catalog";

const taskMocks = vi.hoisted(() => ({
  confirmProfileDraft: vi.fn(),
  createProfileDraft: vi.fn(),
  listProfiles: vi.fn(),
  routerPush: vi.fn(),
  startHecanReading: vi.fn(),
  startPreviewReading: vi.fn(),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: taskMocks.routerPush, replace: vi.fn() }),
  usePathname: () => "/bazi",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
  confirmProfileDraft: taskMocks.confirmProfileDraft,
  createProfileDraft: taskMocks.createProfileDraft,
  listProfiles: taskMocks.listProfiles,
  startHecanReading: taskMocks.startHecanReading,
  startPreviewReading: taskMocks.startPreviewReading,
}));

const confirmedProfile = {
  profile_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  profile_version_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  subject_ref: "profile-version:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  version: 1,
  created_at: "2026-08-27T00:00:00Z",
};

beforeEach(() => {
  taskMocks.confirmProfileDraft.mockReset().mockResolvedValue(confirmedProfile);
  taskMocks.createProfileDraft.mockReset().mockResolvedValue({
    draft_id: "draft-retry-1",
    status: "draft",
  });
  taskMocks.listProfiles.mockReset().mockResolvedValue({ profiles: [] });
  taskMocks.routerPush.mockReset();
  taskMocks.startHecanReading.mockReset();
  taskMocks.startPreviewReading.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
  vi.clearAllMocks();
});

function taskShellCss() {
  return readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
}

async function fillNatalTask(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText("受测对象"), "本人");
  await user.selectOptions(screen.getByLabelText("出生年份"), "1990");
  await user.selectOptions(screen.getByLabelText("出生月份"), "05");
  await user.selectOptions(screen.getByLabelText("出生日期"), "06");
  await user.selectOptions(screen.getByLabelText("出生小时"), "08");
  await user.selectOptions(screen.getByLabelText("出生分钟"), "30");
  await user.selectOptions(screen.getByLabelText("出生省份"), "江苏省");
  await user.selectOptions(screen.getByLabelText("出生城市"), "常州市");
  await user.selectOptions(screen.getByLabelText("出生区县"), "金坛区");
  await user.click(screen.getByRole("radio", { name: "男" }));
}

describe("ProductTaskPage input shell", () => {
  it("cuts the large hero: h1 is 30px and the in-page line is 返回 + 任务名 + one sentence", async () => {
    const css = taskShellCss();
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).not.toMatch(/clamp\(2\.25rem/);
    expect(css).not.toMatch(/\.heroCopy/);

    render(<BaziPage />);
    await waitFor(() => expect(listProfiles).toHaveBeenCalled());

    const heading = screen.getByRole("heading", { level: 1, name: "八字" });
    const line = heading.closest("header");
    expect(heading).toBeVisible();
    expect(line?.textContent).toContain("返回");
    expect(line?.textContent).toContain(PRODUCT_CATALOG.bazi.summary);
    expect(line?.querySelector("a")).toHaveAttribute("href", "/arts");
    expect(line?.querySelector("a")).toHaveTextContent("返回");
  });

  it("uses Pattern 1: a 496px input column with a non-empty trust rail on desktop", async () => {
    const css = taskShellCss();
    expect(css).toMatch(/\.inputLayout\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*496px\)\s*minmax\(0,\s*1fr\)[^}]*align-items:\s*start/s);
    expect(css).toMatch(/@media\s*\(max-width:\s*63\.999rem\)[\s\S]*?\.inputLayout\s*\{[^}]*grid-template-columns:\s*1fr/s);
    expect(css).toMatch(/\.formPanel[\s\S]*?max-width:\s*var\(--container-form\)/);

    render(<BaziPage />);
    await waitFor(() => expect(listProfiles).toHaveBeenCalled());

    const form = screen.getByRole("form", { name: "八字任务输入" });
    expect(form.closest("[data-input-region]")).toHaveAttribute("data-input-region", "first-screen");
    expect(screen.queryByRole("navigation", { name: "八字任务进度" })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText("八字任务输入")).not.toBeInTheDocument();
    expect(screen.queryByText("确认后生成盘面")).not.toBeInTheDocument();
    expect(screen.queryByText("确认后提交到对应计算服务")).not.toBeInTheDocument();

    const trustRail = screen.getByRole("complementary", { name: "提交后的八字盘面预览" });
    expect(trustRail).toBeVisible();
    expect(trustRail).toHaveTextContent("提交后填入你的盘");
    expect(trustRail).toHaveTextContent("示意骨架");
    expect(trustRail).toHaveTextContent("verified_exact");
    expect(trustRail).toHaveTextContent("《滴天髓》");
    expect(trustRail).toHaveTextContent("1. 提交资料");
    expect(trustRail).toHaveTextContent("2. 生成事实盘");
    expect(trustRail).toHaveTextContent("3. 核对引文");
  });

  it("does not put 待接入 in official page, section, or Status titles", () => {
    render(<ProductTaskPage productId="jianxiang" />);

    expect(screen.getByRole("heading", { level: 1 }).textContent).not.toContain("待接入");
    for (const node of Array.from(document.querySelectorAll("h1, legend"))) {
      expect(node.textContent).not.toContain("待接入");
    }
    expect(screen.queryByRole("status", { name: /待接入/ })).not.toBeInTheDocument();
  });

  it("keeps the bazi first screen actionable without dead controls or profile gating", async () => {
    vi.mocked(listProfiles).mockRejectedValueOnce(new ApiError("需要登录", 401));
    const css = taskShellCss();

    render(<BaziPage />);

    const birthGroup = await screen.findByRole("group", { name: /出生资料/ });
    expect(birthGroup).toBeVisible();
    expect(screen.getByRole("group", { name: /出生日期/ })).toBeVisible();
    expect(screen.getByRole("group", { name: /出生时间/ })).toBeVisible();
    expect(screen.queryByRole("group", { name: /历法/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /不知道出生时辰/ })).not.toBeInTheDocument();
    expect(screen.queryByText("排盘资料")).not.toBeInTheDocument();

    const submit = screen.getByRole("button", { name: "立即排盘（免费）· 查看八字四柱" });
    expect(submit).toBeEnabled();
    await waitFor(() => expect(listProfiles).toHaveBeenCalled());
    expect(submit).toBeEnabled();
    expect(submit).toHaveTextContent("立即排盘（免费）· 查看八字四柱");

    expect(css).toMatch(/\.placeSwitch\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
    expect(css).toMatch(/\.main\s*\{[^}]*scroll-padding-bottom:\s*calc\(var\(--nav-bottom\)/s);
  });

  it("does not apply natal unknown-hour treatment on liuyao", () => {
    render(<ProductTaskPage productId="liuyao" />);

    expect(screen.queryByRole("checkbox", { name: /不知道出生时辰/ })).not.toBeInTheDocument();
    expect(screen.queryByText("请填写明确的出生时间。")).not.toBeInTheDocument();
    expect(screen.getByText("确认后生成盘面")).toBeVisible();
  });
});

describe("ProductTaskExperience retained profile drafts", () => {
  it("delays the bazi structure skeleton, then offers a safe return without accepting a late start", async () => {
    taskMocks.listProfiles.mockResolvedValue({ profiles: [confirmedProfile] });
    let releaseStart!: (value: { reading_version_id: string }) => void;
    taskMocks.startPreviewReading.mockReturnValue(new Promise((resolve) => {
      releaseStart = resolve;
    }));
    render(<ProductTaskPage productId="bazi" />);
    expect(await screen.findByText(/本次将直接使用已保存的不可变档案版本/)).toBeVisible();

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(taskMocks.startPreviewReading).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "正在生成盘面…" })).toBeDisabled();
    expect(screen.queryByRole("status", { name: "正在同步八字盘面" })).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(299));
    expect(screen.queryByRole("status", { name: "正在同步八字盘面" })).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByRole("status", { name: "正在同步八字盘面" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "返回录入" })).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(14_700));
    fireEvent.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.queryByRole("status", { name: "正在同步八字盘面" })).not.toBeInTheDocument();

    await act(async () => {
      releaseStart({ reading_version_id: "late-bazi" });
      await Promise.resolve();
    });
    expect(screen.getByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.queryByText("late-bazi")).not.toBeInTheDocument();
  });

  it("stops the start wait at 60 seconds and focuses the retry action", async () => {
    taskMocks.listProfiles.mockResolvedValue({ profiles: [confirmedProfile] });
    taskMocks.startPreviewReading.mockReturnValue(new Promise(() => undefined));
    render(<ProductTaskPage productId="bazi" />);
    expect(await screen.findByText(/本次将直接使用已保存的不可变档案版本/)).toBeVisible();

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    act(() => vi.advanceTimersByTime(60_000));

    expect(screen.getByRole("alert", { name: /排盘等待超过 60 秒/ })).toBeVisible();
    expect(screen.getByRole("button", { name: "重试" })).toHaveFocus();
    expect(screen.queryByRole("status", { name: "正在同步八字盘面" })).not.toBeInTheDocument();
  });

  it("retries the same draft in a regular natal flow after a transient confirm failure", async () => {
    taskMocks.confirmProfileDraft
      .mockRejectedValueOnce(
        new ApiError("确认服务暂时不可用", 503, undefined, "chart_runtime_transport"),
      )
      .mockResolvedValueOnce(confirmedProfile);
    taskMocks.startPreviewReading.mockRejectedValue(new Error("排盘服务暂时不可用"));
    const user = userEvent.setup();
    render(<ProductTaskPage productId="bazi" />);
    await fillNatalTask(user);

    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await waitFor(() => expect(taskMocks.confirmProfileDraft).toHaveBeenCalledTimes(1));
    await user.click(await screen.findByRole("button", { name: "重试" }));
    await waitFor(() => expect(taskMocks.startPreviewReading).toHaveBeenCalledTimes(1));

    expect(taskMocks.createProfileDraft).toHaveBeenCalledTimes(1);
    expect(taskMocks.confirmProfileDraft).toHaveBeenCalledTimes(2);
    expect(taskMocks.confirmProfileDraft.mock.calls[0]?.[0]).toBe("draft-retry-1");
    expect(taskMocks.confirmProfileDraft.mock.calls[1]?.[0]).toBe("draft-retry-1");
  });

  it("retries the same draft in the shared Hecan/Canwen flow after a transient confirm failure", async () => {
    taskMocks.confirmProfileDraft
      .mockRejectedValueOnce(
        new ApiError("确认服务暂时不可用", 503, undefined, "chart_runtime_transport"),
      )
      .mockResolvedValueOnce(confirmedProfile);
    taskMocks.startHecanReading.mockRejectedValue(new Error("合参服务暂时不可用"));
    const user = userEvent.setup();
    render(<ProductTaskPage productId="hecan" />);
    await fillNatalTask(user);
    await user.click(screen.getByRole("checkbox", { name: /八字/ }));
    await user.click(screen.getByRole("checkbox", { name: /紫微/ }));

    await user.click(screen.getByRole("button", { name: /^立即合参/ }));
    await waitFor(() => expect(taskMocks.confirmProfileDraft).toHaveBeenCalledTimes(1));
    await user.click(await screen.findByRole("button", { name: "重试" }));
    await waitFor(() => expect(taskMocks.startHecanReading).toHaveBeenCalledTimes(1));

    expect(taskMocks.createProfileDraft).toHaveBeenCalledTimes(1);
    expect(taskMocks.confirmProfileDraft).toHaveBeenCalledTimes(2);
    expect(taskMocks.confirmProfileDraft.mock.calls[0]?.[0]).toBe("draft-retry-1");
    expect(taskMocks.confirmProfileDraft.mock.calls[1]?.[0]).toBe("draft-retry-1");
  });
});
