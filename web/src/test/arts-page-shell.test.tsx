import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ArtsPage from "@/app/arts/page";

describe("/arts direction-C shell", () => {
  it("keeps the 30px title without construction copy", () => {
    render(<ArtsPage />);

    expect(screen.getByRole("heading", { level: 1, name: "术数总览" })).toBeVisible();
    expect(screen.getByText("按任务选择公开产品。")).toBeVisible();
    expect(screen.queryByText(/内部计算模块|伪装成独立入口|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/provider/i)).not.toBeInTheDocument();
  });

  it("does not change the public product map", () => {
    render(<ArtsPage />);

    for (const href of ["/bazi", "/luming-nayin", "/ziwei", "/qizheng", "/liuyao", "/qimen", "/daliuren", "/jianxiang", "/hecan", "/wenshi"]) {
      expect(document.querySelector(`main a[href="${href}"]`), `missing ${href}`).not.toBeNull();
    }
    expect(screen.getByRole("link", { name: "八字合盘" })).toHaveAttribute("href", "/bazi/hepan");
    expect(screen.getByRole("link", { name: "紫微合盘" })).toHaveAttribute("href", "/ziwei/hepan");
    expect(screen.getByRole("link", { name: "七政合盘" })).toHaveAttribute("href", "/qizheng/hepan");
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);

    const arts = readFileSync(resolve(process.cwd(), "src/app/arts/arts.module.css"), "utf8");
    expect(arts).not.toMatch(/font-size-hero|clamp\(2\.5rem/);
  });

  it("does not put construction chrome on the production file", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/arts/page.tsx"), "utf8");
    expect(source).not.toMatch(/development_code|调试码/);
    expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
    expect(source).not.toMatch(/AppPageHeader/);
    expect(source).toMatch(/AccountSectionShell/);
  });
});
