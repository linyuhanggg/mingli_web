import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import { ProductTaskPage } from "@/components/task/product-task-page";
import { ApiError, listProfiles } from "@/lib/api";
import { PRODUCT_CATALOG } from "@/products/catalog";

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
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
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function taskShellCss() {
  return readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
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
    expect(trustRail).toHaveTextContent("精确匹配《滴天髓·通神论》");
    expect(trustRail).not.toHaveTextContent(/verified_exact|ViewModel|不可变|落库|接纳|句柄|payment_id/);
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

    const submit = screen.getByRole("button", { name: "免费排盘 · 查看四柱" });
    expect(submit).toBeEnabled();
    await waitFor(() => expect(listProfiles).toHaveBeenCalled());
    expect(submit).toBeEnabled();
    expect(submit).toHaveTextContent("免费排盘 · 查看四柱");

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
