import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import LumingNayinPage from "@/app/luming-nayin/page";
import { NATAL_PRODUCTS, PRODUCT_CATALOG } from "@/products/catalog";

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/luming-nayin",
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

const LUMING_LEAD = "填出生资料，先拿到四柱纳音和可回溯的依据。";
const LUMING_LUNAR_HINT = "请填写公历出生日期。";
const LUMING_SUBMIT = "免费排盘 · 查看禄命纳音";

function taskShellCss() {
  return readFileSync(resolve(process.cwd(), "src/components/task/task-shell.module.css"), "utf8");
}

describe("/luming-nayin public input shell", () => {
  it("uses the accepted public-shell lead, lunar hint, and black full-width submit", async () => {
    render(<LumingNayinPage />);

    const heading = screen.getByRole("heading", { level: 1, name: "禄命纳音" });
    const line = heading.closest("header");
    expect(heading).toBeVisible();
    expect(line?.textContent).toContain("返回");
    expect(line?.querySelector("a")).toHaveAttribute("href", "/arts");
    expect(line?.textContent).toContain(LUMING_LEAD);
    expect(PRODUCT_CATALOG["luming-nayin"].summary).toBe(LUMING_LEAD);

    const lunar = await screen.findByRole("radio", { name: "农历" });
    expect(lunar).toBeDisabled();
    expect(screen.getByText(LUMING_LUNAR_HINT)).toBeVisible();
    expect(screen.queryByText("农历时间口径")).not.toBeInTheDocument();
    expect(screen.queryByText(/当前排盘服务需要公历日期/)).not.toBeInTheDocument();

    const submit = screen.getByRole("button", { name: LUMING_SUBMIT });
    expect(submit).toBeVisible();
    expect(submit.className).toMatch(/primaryButton/);

    const css = taskShellCss();
    expect(css).toMatch(/\.primaryButton\s*\{[^}]*width:\s*100%/s);
    expect(css).toMatch(/\.primaryButton\s*\{[^}]*background:\s*var\(--color-action\)/s);
    expect(css).toMatch(/\.primaryButton\s*\{[^}]*border:\s*1px solid var\(--color-action\)/s);
  });

  it("keeps unknown hour disabled on the accepted contract", async () => {
    render(<LumingNayinPage />);

    const checkbox = await screen.findByRole("checkbox", { name: /不知道出生时辰/ });
    expect(checkbox).toBeDisabled();
    expect(screen.getByText("请填写明确的出生时间。")).toBeVisible();
    expect(screen.getByText("确认后生成盘面")).toBeVisible();
  });

  it("does not put luming on the homepage natal map or invent extras", () => {
    expect(NATAL_PRODUCTS.map((product) => product.id)).toEqual(["bazi", "ziwei", "qizheng"]);

    const page = readFileSync(resolve(process.cwd(), "src/app/luming-nayin/page.tsx"), "utf8");
    const form = readFileSync(resolve(process.cwd(), "src/components/task/product-input-form.tsx"), "utf8");
    expect(page).not.toMatch(/§10|§6\.2/);
    expect(form).not.toMatch(/当前排盘服务需要公历日期/);
    expect(page).not.toMatch(/meihua|taiyi|selection|fengshui/);
  });
});
