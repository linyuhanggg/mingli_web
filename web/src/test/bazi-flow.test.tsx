import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BaziFlow } from "@/components/bazi-flow";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
  syncBaziChart: vi.fn(),
  startPreviewReading: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: navigation.push,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listProfiles: api.listProfiles,
    syncBaziChart: api.syncBaziChart,
    startPreviewReading: api.startPreviewReading,
  };
});

const profileVersionId = "22222222-2222-4222-8222-222222222222";

beforeEach(() => {
  navigation.push.mockReset();
  api.listProfiles.mockReset();
  api.syncBaziChart.mockReset();
  api.startPreviewReading.mockReset();
  api.listProfiles.mockResolvedValue({
    profiles: [
      {
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: profileVersionId,
        subject_ref: `profile-version:${profileVersionId}`,
        version: 1,
        created_at: "2026-08-09T12:00:00Z",
      },
    ],
  });
  api.startPreviewReading.mockResolvedValue({
    reading_version_id: "33333333-3333-4333-8333-333333333333",
  });
  api.syncBaziChart.mockResolvedValue({
    profile_version_id: profileVersionId,
    status: "ready",
    chart_handle: null,
    fact_panel: {
      question: "查看这个档案的确定性八字盘。",
      vocabulary: [],
      facts: [
        {
          ref: "fact:profile/calculated/bazi/four_pillars",
          subject_ref: `profile-version:${profileVersionId}`,
          kind_id: "kind.fact",
          value: {
            year: "甲子",
            month: "乙丑",
            day: "丙寅",
            hour: "丁卯",
          },
          display_text: "four_pillars：{}",
        },
      ],
      evidence: [],
      findings: [],
      claim_scopes: [],
      limits: [],
      prior_answer: null,
      request_view: null,
    },
    input_request: null,
  });
});

describe("BaziFlow", () => {
  it("syncs a server chart in place without starting a reading", async () => {
    const user = userEvent.setup();
    render(<BaziFlow />);

    await user.selectOptions(await screen.findByLabelText("档案版本"), profileVersionId);
    expect(screen.getByText(/本页只展示 Runtime 返回的结构化事实/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "同步排盘" }));

    await waitFor(() => expect(api.syncBaziChart).toHaveBeenCalledTimes(1));
    expect(api.syncBaziChart).toHaveBeenCalledWith(
      { profile_version_id: profileVersionId },
      expect.any(String),
    );
    expect(api.startPreviewReading).not.toHaveBeenCalled();
    expect(navigation.push).not.toHaveBeenCalled();
    expect(await screen.findByText("命盘已就绪")).toBeVisible();
    expect(screen.getByText("甲子")).toBeVisible();
  });

  it("keeps the existing career preview as an explicit deep-reading CTA", async () => {
    const user = userEvent.setup();
    render(<BaziFlow />);

    await user.selectOptions(await screen.findByLabelText("档案版本"), profileVersionId);
    await user.click(screen.getByRole("button", { name: "同步排盘" }));
    await screen.findByText("命盘已就绪");

    await user.click(
      screen.getByRole("button", { name: "进入事业深度解读" }),
    );

    await waitFor(() =>
      expect(api.startPreviewReading).toHaveBeenCalledWith(
        {
          profile_version_id: profileVersionId,
          dimension_ids: ["career"],
          query: "查看这个档案的事业与工作主题",
        },
        expect.any(String),
      ),
    );
    expect(navigation.push).toHaveBeenCalledWith(
      "/app/readings/33333333-3333-4333-8333-333333333333",
    );
  });
});
