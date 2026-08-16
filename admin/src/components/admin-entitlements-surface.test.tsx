import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminEntitlementsSurface } from "@/components/admin-entitlements-surface";
import type { AdminEntitlementEvent, AdminEntitlementEventsResponse } from "@/lib/admin-entitlements";

const event: AdminEntitlementEvent = {
  id: "event-1",
  owner_user_id: "user-1",
  entitlement_id: "manual:case-1",
  kind: "GRANT",
  quantity: 2,
  source_type: "admin_grant",
  source_ref: "case-1-grant",
  target_ref: "support-case-1",
  created_at: "2026-08-14T01:00:00Z",
};

describe("AdminEntitlementsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows recent ledger facts and appends an audited adjustment", async () => {
    const user = userEvent.setup();
    const response: AdminEntitlementEventsResponse = { events: [event] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: { event, created: true } })
      .mockResolvedValueOnce({ ok: true, data: response });

    render(<AdminEntitlementsSurface role="finance" />);

    expect(await screen.findByText("manual:case-1")).toBeVisible();
    await user.type(screen.getByLabelText("用户 ID"), "user-1");
    await user.type(screen.getByLabelText("权益 ID"), "manual:case-1");
    await user.type(screen.getByLabelText("操作原因"), "客服补发体验次数");
    await user.type(screen.getByLabelText("来源编号"), "case-1-grant");
    await user.click(screen.getByRole("button", { name: "追加账本事件" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/entitlements/events",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          owner_user_id: "user-1",
          entitlement_id: "manual:case-1",
          action: "grant",
          quantity: 1,
          reason: "客服补发体验次数",
          source_ref: "case-1-grant",
          target_ref: null,
        }),
      }),
    );
    expect(await screen.findByText("权益账本事件已追加")).toBeVisible();
  });

  it("does not expose ledger adjustment controls to support", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { events: [] } });

    render(<AdminEntitlementsSurface role="support" />);

    expect(await screen.findByText("暂无权益账本事件")).toBeVisible();
    expect(screen.queryByRole("button", { name: "追加账本事件" })).not.toBeInTheDocument();
  });
});
