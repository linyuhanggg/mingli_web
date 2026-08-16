import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminAppealsSurface } from "@/components/admin-appeals-surface";
import type { AdminReferralAppeal, AdminReferralAppealsResponse } from "@/lib/admin-appeals";

const appeal: AdminReferralAppeal = {
  id: "appeal-1",
  attribution_id: "attribution-1",
  requester_user_id: "user-2",
  inviter_user_id: "user-1",
  status: "correction_pending",
  reason: "客户提供了支付与归因证据，申请复核。",
  decision_reason: "需要纠正已确认的技术错误。",
  created_at: "2026-08-14T00:00:00Z",
  decided_at: null,
  approval_count: 1,
  risk_signals: [
    {
      id: "signal-1",
      signal_type: "device_overlap",
      severity: "medium",
      reason: "设备信号重合，仅作为风险提示。",
      created_by_staff_user_id: "staff-1",
      created_at: "2026-08-14T00:00:00Z",
    },
  ],
  approvals: [
    {
      id: "approval-1",
      staff_user_id: "staff-1",
      reason: "需要纠正已确认的技术错误。",
      created_at: "2026-08-14T00:00:00Z",
    },
  ],
  correction_event_id: null,
  correction_event_kind: null,
  participation_restriction_user_ids: [],
};

describe("AdminAppealsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("lets support submit an appeal application without decision controls", async () => {
    const user = userEvent.setup();
    const response: AdminReferralAppealsResponse = { appeals: [] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: appeal })
      .mockResolvedValueOnce({ ok: true, data: { appeals: [appeal] } });

    render(<AdminAppealsSurface role="support" />);

    expect(await screen.findByText("暂无邀请申诉")).toBeVisible();
    await user.type(screen.getByRole("textbox", { name: "归因编号" }), "attribution-1");
    await user.type(screen.getByRole("textbox", { name: "申诉理由" }), "请复核客户提供的支付证据");
    await user.click(screen.getByRole("button", { name: "提交邀请申诉" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/appeals",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          attribution_id: "attribution-1",
          reason: "请复核客户提供的支付证据",
        }),
      }),
    );
    expect(await screen.findByText("邀请申诉已提交")).toBeVisible();
    expect(screen.queryByRole("button", { name: "提交申诉决定" })).not.toBeInTheDocument();
  });

  it("shows risk signals and lets finance submit a correction decision", async () => {
    const user = userEvent.setup();
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: { appeals: [appeal] } })
      .mockResolvedValueOnce({ ok: true, data: { ...appeal, status: "corrected", approval_count: 2, participation_restriction_user_ids: ["user-1", "user-2"] } })
      .mockResolvedValueOnce({ ok: true, data: { appeals: [{ ...appeal, status: "corrected", approval_count: 2, participation_restriction_user_ids: ["user-1", "user-2"] }] } });

    render(<AdminAppealsSurface role="finance" />);

    expect(await screen.findByText("device_overlap · medium")).toBeVisible();
    expect(screen.getByText("审批 1/2")).toBeVisible();
    expect(screen.getByText("未来参与限制：0/2")).toBeVisible();
    expect(screen.queryByRole("button", { name: "提交邀请申诉" })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "申诉决定" }), "correction");
    await user.type(screen.getByRole("textbox", { name: "决定原因" }), "第二位审核员确认纠正");
    await user.click(screen.getByRole("button", { name: "提交申诉决定" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/appeals/appeal-1/decision",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ outcome: "correction", reason: "第二位审核员确认纠正" }),
      }),
    );
    expect(await screen.findByText("申诉决定已提交")).toBeVisible();
  });
});
