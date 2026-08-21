import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AccountPage from "@/app/account/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

describe("/account entry shell", () => {
  it("keeps the 30px title without construction copy", () => {
    render(<AccountPage />);

    expect(screen.getByRole("heading", { level: 1, name: "我的" })).toBeVisible();
    expect(screen.getByText("查看账号、档案、历史和设置。")).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByText(/从这里查看当前账号|追加式权益账本|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome or DESIGN §10 / §6.2 on the production file", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/account/page.tsx"), "utf8");
    expect(source).not.toMatch(/development_code|调试码/);
    expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
    expect(source).not.toMatch(/AppPageHeader/);
    expect(source).toMatch(/AccountSectionShell/);
  });
});
