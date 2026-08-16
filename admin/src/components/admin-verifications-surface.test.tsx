import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminVerificationsSurface } from "@/components/admin-verifications-surface";

describe("AdminVerificationsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows verification sources and outcomes without feedback notes", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        events: [
          {
            id: "event-1",
            source: "claim",
            reading_version_id: "reading-version-1",
            claim_id: "claim:career",
            outcome: "accepted",
            actor_ref: "user-1",
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminVerificationsSurface role="support" />);

    expect(await screen.findByText("Claim 核对")).toBeVisible();
    expect(screen.getByText("已接受")).toBeVisible();
    expect(screen.getByText("claim:career")).toBeVisible();
    expect(screen.queryByText("private claim note")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/verifications?limit=100");
  });

  it("does not expose verification data to finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Verification read permission required",
    });

    render(<AdminVerificationsSurface role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("Claim 核对")).not.toBeInTheDocument();
  });
});
