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

afterEach(cleanup);

function taskShellCss() {
  return readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
}

describe("ProductTaskPage input shell", () => {
  it("cuts the large hero: h1 is 30px and the in-page line is 返回 + 任务名 + one sentence", () => {
    const css = taskShellCss();
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).not.toMatch(/clamp\(2\.25rem/);
    expect(css).not.toMatch(/\.heroCopy/);

    render(<BaziPage />);

    const heading = screen.getByRole("heading", { level: 1, name: "八字" });
    const line = heading.closest("header");
    expect(heading).toBeVisible();
    expect(line?.textContent).toContain("返回");
    expect(line?.textContent).toContain(PRODUCT_CATALOG.bazi.summary);
    expect(line?.querySelector("a")).toHaveAttribute("href", "/arts");
    expect(line?.querySelector("a")).toHaveTextContent("返回");
  });

  it("keeps the first screen as a centered 496px form without hanging progress or ModulePlan", () => {
    const css = taskShellCss();
    expect(css).toMatch(/\.formPanel[\s\S]*?max-width:\s*var\(--container-form\)/);
    expect(css).toMatch(/\.inputLayout\s*\{[^}]*justify-items:\s*center/s);
    expect(css).not.toMatch(
      /grid-template-columns:\s*minmax\(0,\s*var\(--container-form\)\)\s*minmax\(18rem/,
    );

    render(<BaziPage />);

    const form = screen.getByRole("form", { name: "八字任务输入" });
    expect(form.closest("[data-input-region]")).toHaveAttribute("data-input-region", "first-screen");
    expect(screen.queryByRole("navigation", { name: "八字任务进度" })).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /四柱与五行力量/ })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText("八字任务输入")).not.toBeInTheDocument();
    expect(screen.queryByText("确认后生成盘面")).not.toBeInTheDocument();
    expect(screen.queryByText("确认后提交到对应计算服务")).not.toBeInTheDocument();
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

    expect(screen.getByRole("group", { name: /出生资料/ })).toBeVisible();
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
