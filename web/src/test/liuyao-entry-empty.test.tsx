import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";
import {
  LIUYAO_ENTRY_CASTING_HINT,
  LIUYAO_ENTRY_SILHOUETTE_CAPTION,
  LIUYAO_ENTRY_SUITABILITY,
} from "@/components/task/liuyao-entry-copy";
import { PRODUCT_CATALOG } from "@/products/catalog";

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/liuyao",
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

describe("/liuyao S0 empty copy", () => {
  it("shows the accepted S0 strings without inventing catalog summary, sample lines, or numbered promises", () => {
    expect(LIUYAO_ENTRY_SUITABILITY.length).toBeGreaterThan(0);
    expect(LIUYAO_ENTRY_SUITABILITY.length).toBeLessThanOrEqual(20);

    render(<ProductTaskPage productId="liuyao" />);

    const heading = screen.getByRole("heading", { level: 1, name: "六爻" });
    const line = heading.closest("header");
    expect(line).toHaveTextContent("六爻");
    expect(line).toHaveTextContent(LIUYAO_ENTRY_SUITABILITY);
    expect(line).not.toHaveTextContent(PRODUCT_CATALOG.liuyao.summary);
    expect(screen.getByText(LIUYAO_ENTRY_CASTING_HINT)).toBeVisible();
    expect(screen.getByText(LIUYAO_ENTRY_SILHOUETTE_CAPTION)).toBeVisible();
    expect(screen.getByRole("figure", { name: "六爻空盘剪影" })).toBeVisible();
    expect(screen.getByLabelText("当前问题")).toBeVisible();
    expect(screen.getByLabelText("起卦方式")).toBeVisible();
    expect(screen.getByLabelText("事件时间")).toBeVisible();
    expect(screen.queryByText("乾为天")).not.toBeInTheDocument();
    expect(screen.queryByText("甲子")).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: /模块/ })).not.toBeInTheDocument();
  });

  it("keeps the empty silhouette hidden at 360 and dual-column from 1024 without changing the shared page-line size", () => {
    const css = taskShellCss();
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).toMatch(
      /\.experience\[data-product="liuyao"\]\[data-stage="input"\] \.inputLayout\s*\{[^}]*grid-template-columns:\s*minmax\(28\.5rem,\s*31rem\)\s*minmax\(26\.25rem,\s*1fr\)/s,
    );
    expect(css).toMatch(/@media \(max-width: 63\.999rem\)[\s\S]*\.liuyaoSilhouette\s*\{[^}]*max-height:\s*7\.5rem/s);
    expect(css).toMatch(/@media \(max-width: 22\.5rem\)[\s\S]*\.liuyaoSilhouette\s*\{[^}]*display:\s*none/s);
  });
});
