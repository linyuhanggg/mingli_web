import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminAuditSurface } from "@/components/admin-audit-surface";
import type { AdminAuditResponse } from "@/lib/admin-audit";

describe("AdminAuditSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows redacted audit facts without arbitrary metadata", async () => {
    const response: AdminAuditResponse = {
      events: [
        {
          id: "audit-1",
          action: "catalog.version.published",
          actor: "ops@example.com",
          metadata: {
            reason: "通过商品发布检查",
            target_id: "version-1",
          },
          created_at: "2026-08-14T01:00:00Z",
        },
      ],
    };
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: response });

    render(<AdminAuditSurface role="superadmin" />);

    expect(await screen.findByText("catalog.version.published")).toBeVisible();
    expect(screen.getByText("ops@example.com")).toBeVisible();
    expect(screen.getByText("version-1")).toBeVisible();
    expect(screen.getByText("脱敏读取")).toBeVisible();
    expect(screen.queryByText("do-not-expose")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/audit");
  });

  it("renders the server permission boundary for a forbidden response", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Audit reader permission required",
    });

    render(<AdminAuditSurface role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
