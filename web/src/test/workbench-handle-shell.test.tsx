import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WorkbenchRecoveryPage from "@/app/workbench/[handle]/page";

describe("/workbench/[handle] direction-C shell", () => {
  it("keeps the 30px title without construction copy", async () => {
    const page = await WorkbenchRecoveryPage({
      params: Promise.resolve({ handle: "opaque-task-01" }),
    });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "恢复任务" })).toBeVisible();
    expect(screen.getByText("用不透明编号查找任务，再回到原来的产品页。")).toBeVisible();
    expect(screen.getByText("opaque-task-01")).toBeVisible();
    expect(document.querySelector('[data-state="unavailable"]')).not.toBeNull();
    expect(screen.queryByText(/任务句柄|尚未接入|不透明句柄|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("keeps the return action black and full width", async () => {
    const page = await WorkbenchRecoveryPage({
      params: Promise.resolve({ handle: "opaque-task-01" }),
    });
    render(page);

    expect(screen.getByRole("link", { name: "返回任务选择" })).toHaveAttribute("href", "/");

    const css = readFileSync(
      resolve(process.cwd(), "src/app/workbench/[handle]/recovery.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.homeLink\s*\{[^}]*width:\s*100%/s);
    expect(css).toMatch(/\.homeLink\s*\{[^}]*background:\s*var\(--color-action\)/s);
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);

    const recovery = readFileSync(
      resolve(process.cwd(), "src/app/workbench/[handle]/recovery.module.css"),
      "utf8",
    );
    expect(recovery).not.toMatch(/font-size-hero|clamp\(2\.5rem/);
  });

  it("does not put construction chrome on the production file", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/app/workbench/[handle]/page.tsx"),
      "utf8",
    );
    expect(source).not.toMatch(/development_code|调试码/);
    expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
    expect(source).not.toMatch(/AppPageHeader|尚未接入|任务句柄/);
    expect(source).toMatch(/AccountSectionShell/);
  });
});
