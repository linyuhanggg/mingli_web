import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import BaziRelationshipPage from "@/app/bazi/hepan/page";
import QizhengRelationshipPage from "@/app/qizheng/hepan/page";
import ZiweiRelationshipPage from "@/app/ziwei/hepan/page";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: vi.fn(),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("hepan three-page shell", () => {
  it.each([
    ["八字", BaziRelationshipPage],
    ["紫微", ZiweiRelationshipPage],
    ["七政", QizhengRelationshipPage],
  ] as const)("keeps %s on a 30px title without construction copy or a profile picker", (name, Page) => {
    render(<Page />);

    expect(screen.getByRole("heading", { level: 1, name: `${name}双人合盘` })).toBeVisible();
    expect(screen.getByText("填写双方资料和关系。")).toBeVisible();
    expect(screen.getByRole("link", { name: "返回" })).toBeVisible();
    expect(screen.getByRole("group", { name: "甲方资料" })).toBeVisible();
    expect(screen.getByRole("group", { name: "乙方资料" })).toBeVisible();
    expect(screen.getByLabelText("关系类型")).toBeVisible();
    expect(screen.getByRole("button", { name: "生成合盘" })).toBeEnabled();
    expect(screen.getAllByRole("button", { name: "生成合盘" })).toHaveLength(1);
    expect(screen.queryByText(/双方结构事实|ViewModel|Runtime|ProfileVersion|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/选择已有档案|已有档案/)).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: /已有档案/ })).not.toBeInTheDocument();
  });

  it("does not change the queued party-B default", () => {
    render(<BaziRelationshipPage />);
    const subjectSelects = screen.getAllByLabelText(/资料主体/);
    expect(subjectSelects).toHaveLength(2);
    expect(subjectSelects[0]).toHaveValue("self");
    expect(subjectSelects[1]).toHaveValue("self");
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/relationship/relationship-task-page.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.pageLine h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put a profile picker on the production files", () => {
    for (const file of [
      "src/app/bazi/hepan/page.tsx",
      "src/app/ziwei/hepan/page.tsx",
      "src/app/qizheng/hepan/page.tsx",
      "src/components/relationship/relationship-task-page.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/listProfiles|选择已有档案|已有档案选择器/);
      expect(source).not.toMatch(/§10|§6\.2|SecondarySurfaceFrame|AppPageHeader/);
    }
  });
});
