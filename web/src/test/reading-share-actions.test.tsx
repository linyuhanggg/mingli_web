import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingSharePanel } from "@/components/readings/reading-share-panel";

const api = vi.hoisted(() => ({
  createReadingShare: vi.fn(),
  revokeReadingShare: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  createReadingShare: api.createReadingShare,
  revokeReadingShare: api.revokeReadingShare,
}));

const readingId = "33333333-3333-4333-8333-333333333333";
const share = {
  snapshot_id: "55555555-5555-4555-8555-555555555555",
  token: "opaque-share-token",
  expires_at: "2026-08-15T05:00:00Z",
};

beforeEach(() => {
  api.createReadingShare.mockReset();
  api.revokeReadingShare.mockReset();
  api.createReadingShare.mockResolvedValue(share);
  api.revokeReadingShare.mockResolvedValue(undefined);
});

describe("ReadingSharePanel", () => {
  it("creates an opaque short-lived link and revokes the same snapshot", async () => {
    const user = userEvent.setup();
    render(<ReadingSharePanel readingId={readingId} />);

    await user.click(screen.getByRole("button", { name: "创建 24 小时分享" }));
    expect(api.createReadingShare).toHaveBeenCalledWith(readingId, 86_400);
    expect(await screen.findByRole("link", { name: "打开分享页" })).toHaveAttribute(
      "href",
      "/share/opaque-share-token",
    );
    expect(screen.getByText(/有效至/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "撤销分享" }));
    expect(api.revokeReadingShare).toHaveBeenCalledWith(readingId, share.snapshot_id);
    expect(await screen.findByRole("button", { name: "创建 24 小时分享" })).toBeVisible();
  });
});
