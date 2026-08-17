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

describe("share route wiring", () => {
  it("renders a valid short-lived share document from the token API", async () => {
    api.getReadingShare.mockResolvedValue({ document: sharedDocument });

    const page = await SharePage({
      params: Promise.resolve({ shareId: "opaque-share-token" }),
    });
    render(page);

    expect(await screen.findByRole("heading", { name: "分享中的解读" })).toBeVisible();
    expect(screen.getByText("先稳住长期积累。")).toBeVisible();
    expect(screen.getByText("先完成可持续的基础动作。")).toBeVisible();
    expect(screen.getByText("仅供个人参考。")).toBeVisible();
    expect(api.getReadingShare).toHaveBeenCalledWith("opaque-share-token");
  });

  it("keeps expired or revoked snapshots unavailable", async () => {
    api.getReadingShare.mockRejectedValue(new ApiError("Share unavailable", 404));

    const page = await SharePage({
      params: Promise.resolve({ shareId: "expired-share-token" }),
    });
    render(page);

    expect(await screen.findByRole("alert", { name: "分享不可用" })).toBeVisible();
    expect(screen.queryByText("先稳住长期积累。")).not.toBeInTheDocument();
  });
});
