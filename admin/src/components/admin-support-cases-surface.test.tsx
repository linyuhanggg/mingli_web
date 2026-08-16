import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminSupportCasesSurface } from "@/components/admin-support-cases-surface";
import type { AdminSupportCasesResponse } from "@/lib/admin-support-cases";

const supportCase = {
  id: "case-1",
  owner_user_id: "user-1",
  subject_ref: "reading:version-1",
  category: "delivery" as const,
  summary: "用户反馈报告未显示",
  status: "open" as const,
  created_by_staff_user_id: "staff-1",
  created_at: "2026-08-14T00:00:00Z",
  updated_at: "2026-08-14T00:00:00Z",
};

describe("AdminSupportCasesSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("lists real cases and lets support submit an audited application", async () => {
    const user = userEvent.setup();
    const response: AdminSupportCasesResponse = { cases: [supportCase] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: { ...supportCase, id: "case-2" } })
      .mockResolvedValueOnce({ ok: true, data: response });

    render(<AdminSupportCasesSurface role="support" />);

    expect(await screen.findByText("reading:version-1")).toBeVisible();
    expect(screen.getByText("用户反馈报告未显示")).toBeVisible();
    await user.type(screen.getByRole("textbox", { name: "对象编号" }), "user-2");
    await user.type(screen.getByRole("textbox", { name: "案件摘要" }), "需要人工确认交付");
    await user.type(screen.getByRole("textbox", { name: "操作原因" }), "记录客服申请并转运营");
    await user.click(screen.getByRole("button", { name: "提交客服案件" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/support-cases",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          owner_user_id: null,
          subject_ref: "user-2",
          category: "account",
          summary: "需要人工确认交付",
          reason: "记录客服申请并转运营",
        }),
      }),
    );
    expect(await screen.findByText("客服案件已提交")).toBeVisible();
  });

  it("keeps the submission form out of finance read-only mode", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { cases: [] } });

    render(<AdminSupportCasesSurface role="finance" />);

    expect(await screen.findByText("暂无客服案件")).toBeVisible();
    expect(screen.queryByRole("button", { name: "提交客服案件" })).not.toBeInTheDocument();
  });

  it("offers the operational correction and review queues", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { cases: [] } });

    render(<AdminSupportCasesSurface role="support" />);

    expect(await screen.findByText("暂无客服案件")).toBeVisible();
    expect(screen.getByRole("option", { name: "资料纠正" })).toBeVisible();
    expect(screen.getByRole("option", { name: "算法复核" })).toBeVisible();
    expect(screen.getByRole("option", { name: "售后" })).toBeVisible();
    expect(screen.getByRole("option", { name: "补偿" })).toBeVisible();
  });
});
