import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ArtsPage from "@/app/arts/page";
import BaziRelationshipPage from "@/app/bazi/hepan/page";
import QizhengRelationshipPage from "@/app/qizheng/hepan/page";
import WorkbenchRecoveryPage from "@/app/workbench/[handle]/page";
import ZiweiRelationshipPage from "@/app/ziwei/hepan/page";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(cleanup);

describe("product directory and relationship routes", () => {
  it("lists the frozen public products without exposing provider keys", () => {
    render(<ArtsPage />);
    for (const href of ["/bazi", "/ziwei", "/qizheng", "/liuyao", "/qimen", "/daliuren", "/jianxiang", "/hecan", "/wenshi"]) {
      expect(document.querySelector(`main a[href="${href}"]`), `missing ${href}`).not.toBeNull();
    }
    expect(screen.queryByText(/provider/i)).not.toBeInTheDocument();
    expect(screen.queryByText("页面已预制")).not.toBeInTheDocument();
  });

  it.each([
    ["八字", BaziRelationshipPage],
    ["紫微", ZiweiRelationshipPage],
    ["七政", QizhengRelationshipPage],
  ] as const)("%s relationship route has two people and a relationship workspace", (name, Page) => {
    render(<Page />);
    expect(screen.getByRole("form", { name: `${name}双人合盘输入` })).toBeVisible();
    expect(screen.getByRole("group", { name: "甲方资料" })).toBeVisible();
    expect(screen.getByRole("group", { name: "乙方资料" })).toBeVisible();
    expect(screen.getByLabelText("关系类型")).toBeVisible();
    expect(screen.getByText("甲方 / 乙方 / 关系区")).toBeVisible();
    expect(document.querySelector('[data-state="processing"]')).not.toBeNull();
    expect(screen.queryByText("页面已预制")).not.toBeInTheDocument();
  });

  it("keeps opaque workbench recovery honest when the resolver is unavailable", async () => {
    const page = await WorkbenchRecoveryPage({ params: Promise.resolve({ handle: "opaque-task-01" }) });
    render(page);
    expect(screen.getByRole("heading", { level: 1, name: "恢复任务" })).toBeVisible();
    expect(screen.getByText("opaque-task-01")).toBeVisible();
    expect(document.querySelector('[data-state="unavailable"]')).not.toBeNull();
    expect(screen.queryByText("页面已预制")).not.toBeInTheDocument();
  });
});
