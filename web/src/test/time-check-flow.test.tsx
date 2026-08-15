import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TimeCheckFlow } from "@/components/time-check-flow";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush }),
  useSearchParams: () => new URLSearchParams(),
}));

const api = vi.hoisted(() => ({
  createIdempotencyKey: vi.fn(),
  formatProfileOption: vi.fn((profile: { version: number }) => `档案 ${profile.version}`),
  listProfiles: vi.fn(),
  startTimeCheckReading: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

const profiles = [
  {
    profile_id: "profile-1",
    profile_version_id: "version-1",
    subject_ref: "profile-version:version-1",
    version: 1,
    created_at: "2026-08-10T01:00:00Z",
  },
];

beforeEach(() => {
  routerPush.mockReset();
  api.createIdempotencyKey.mockReset();
  api.createIdempotencyKey.mockReturnValue("time-check-intent-1");
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles });
  api.startTimeCheckReading.mockReset();
  api.startTimeCheckReading.mockResolvedValue({
    reading_version_id: "reading-version-1",
  });
});

describe("TimeCheckFlow", () => {
  it("starts twelve candidate facts from a confirmed profile and time range", async () => {
    const user = userEvent.setup();
    render(<TimeCheckFlow />);

    await screen.findByLabelText("档案版本");
    expect(screen.queryByLabelText(/结构化事件/)).not.toBeInTheDocument();
    expect(screen.getByText(/真实产品路由暂不接受这类输入/)).toBeVisible();
    await user.clear(screen.getByLabelText("已知时间范围·开始"));
    await user.type(screen.getByLabelText("已知时间范围·开始"), "05:00");
    await user.clear(screen.getByLabelText("已知时间范围·结束"));
    await user.type(screen.getByLabelText("已知时间范围·结束"), "07:00");
    await user.type(
      screen.getByLabelText("可核对事件（可选，每行一条，最多 5 条）"),
      "第一次搬家\n开始工作",
    );
    await user.click(screen.getByRole("button", { name: /生成十二候选事实/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/readings/reading-version-1"),
    );
    expect(api.startTimeCheckReading).toHaveBeenCalledWith(
      {
        profile_version_id: "version-1",
        time_range_start: "05:00",
        time_range_end: "07:00",
        known_events: ["第一次搬家", "开始工作"],
        query: "围绕已确认出生档案生成十二个候选时辰事实",
        dimension_ids: ["time_options"],
      },
      "time-check-intent-1",
    );
  });

  it("rejects more than five event lines before submitting", async () => {
    const user = userEvent.setup();
    render(<TimeCheckFlow />);

    const events = await screen.findByLabelText("可核对事件（可选，每行一条，最多 5 条）");
    await user.type(events, "一\n二\n三\n四\n五\n六");
    await user.click(screen.getByRole("button", { name: /生成十二候选事实/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "最多填写 5 条可核对事件",
    );
    expect(api.startTimeCheckReading).not.toHaveBeenCalled();
  });
});
