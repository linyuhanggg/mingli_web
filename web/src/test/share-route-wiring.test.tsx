import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SharePage from "@/app/share/[shareId]/page";
import { ApiError, type ReadingShareDocument } from "@/lib/api";

const api = vi.hoisted(() => ({
  getReadingShare: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getReadingShare: api.getReadingShare,
}));

const sharedDocument: ReadingShareDocument = {
  schema_version: "shared-reading-document/v1",
  document_id: "document-1",
  reading_version_id: "33333333-3333-4333-8333-333333333333",
  accepted_copy_ref: "accepted-copy-1",
  product_version: "bazi-v1",
  presentation_contract_version: "presentation-v1",
  answer_summary: "先稳住长期积累。",
  themes: [{ theme_id: "career", label: "事业" }],
  claims: [
    {
      claim_id: "claim-1",
      text: "先完成可持续的基础动作。",
    },
  ],
  evidence: [
    {
      evidence_ref: "evidence-1",
      title: "服务端确定性事实",
    },
  ],
  boundaries: [{ limit_ref: "limit-1", text: "仅供个人参考。" }],
  versions: {
    runtime_release: "runtime-v1",
    view_model_schema: "bazi-chart/v1",
    reading_document_schema: "reading-document/v1",
  },
};

beforeEach(() => {
  api.getReadingShare.mockReset();
});

function expectShareChrome() {
  expect(screen.getByRole("heading", { level: 1, name: "分享" })).toBeVisible();
  expect(screen.getByText("查看这份已确认的分享。")).toBeVisible();
}

describe("share route wiring", () => {
  it("renders a valid short-lived share document from the token API", async () => {
    api.getReadingShare.mockResolvedValue({ document: sharedDocument });

    const page = await SharePage({
      params: Promise.resolve({ shareId: "opaque-share-token" }),
    });
    render(page);

    expectShareChrome();
    expect(await screen.findByText("先稳住长期积累。")).toBeVisible();
    expect(screen.getByText("先完成可持续的基础动作。")).toBeVisible();
    expect(screen.getByText("仅供个人参考。")).toBeVisible();
    expect(screen.queryByText("document-1")).not.toBeInTheDocument();
    expect(screen.queryByText("accepted-copy-1")).not.toBeInTheDocument();
    expect(screen.queryByText("33333333-3333-4333-8333-333333333333")).not.toBeInTheDocument();
    expect(screen.queryByText("runtime-v1")).not.toBeInTheDocument();
    expect(api.getReadingShare).toHaveBeenCalledWith("opaque-share-token");
  });

  it("keeps expired or revoked snapshots unavailable", async () => {
    api.getReadingShare.mockRejectedValue(new ApiError("Share unavailable", 404));

    const page = await SharePage({
      params: Promise.resolve({ shareId: "expired-share-token" }),
    });
    render(page);

    expectShareChrome();
    expect(await screen.findByRole("alert", { name: "分享不可用" })).toBeVisible();
    expect(screen.getByText("分享已过期、被撤销，或不存在。")).toBeVisible();
    expect(screen.getByRole("button", { name: "返回首页" })).toBeVisible();
    expect(screen.queryByText("先稳住长期积累。")).not.toBeInTheDocument();
    expect(screen.queryByText("分享中的解读")).not.toBeInTheDocument();
  });

  it("does not guess content when the share has been revoked", async () => {
    api.getReadingShare.mockRejectedValue(new ApiError("Share gone", 410));

    const page = await SharePage({
      params: Promise.resolve({ shareId: "revoked-share-token" }),
    });
    render(page);

    expect(await screen.findByRole("alert", { name: "分享不可用" })).toBeVisible();
    expect(screen.queryByText("先稳住长期积累。")).not.toBeInTheDocument();
    expect(screen.queryByText("Share gone")).not.toBeInTheDocument();
  });

  it("does not put a construction Status shell on the production share files", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/auth-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).toMatch(/button\[type="submit"\][^}]*background:\s*var\(--color-action\)/s);

    for (const file of [
      "src/app/share/[shareId]/page.tsx",
      "src/components/shared-reading-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondaryStatus|StatusPanel|authGrid|SecondarySurfaceFrame/);
      expect(source).not.toMatch(/owner_|分享者账户|不会重新计算盘面/);
    }
  });
});
