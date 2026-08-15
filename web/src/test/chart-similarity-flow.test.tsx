import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChartSimilarityFlow } from "@/components/chart-similarity-flow";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush }),
  useSearchParams: () => new URLSearchParams(),
}));

const api = vi.hoisted(() => ({
  createIdempotencyKey: vi.fn(),
  formatProfileOption: vi.fn((profile: { version: number }) => `档案 ${profile.version}`),
  listProfiles: vi.fn(),
  startChartSimilarityReading: vi.fn(),
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
  {
    profile_id: "profile-2",
    profile_version_id: "version-2",
    subject_ref: "profile-version:version-2",
    version: 2,
    created_at: "2026-08-11T01:00:00Z",
  },
];

beforeEach(() => {
  routerPush.mockReset();
  api.createIdempotencyKey.mockReset();
  api.createIdempotencyKey.mockReturnValue("chart-similarity-intent-1");
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles });
  api.startChartSimilarityReading.mockReset();
  api.startChartSimilarityReading.mockResolvedValue({
    reading_version_id: "reading-version-1",
  });
});

describe("ChartSimilarityFlow", () => {
  it("starts a bounded comparison from two confirmed profile versions", async () => {
    const user = userEvent.setup();
    render(<ChartSimilarityFlow />);

    const left = await screen.findByLabelText("左侧已确认档案");
    const right = screen.getByLabelText("右侧已确认档案");
    await user.selectOptions(left, "version-2");
    await user.selectOptions(right, "version-1");
    await user.click(screen.getByRole("button", { name: /开始比较四柱事实/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/readings/reading-version-1"),
    );
    expect(api.startChartSimilarityReading).toHaveBeenCalledWith(
      {
        profile_version_ids: ["version-2", "version-1"],
        query: "请比较两份已确认命盘的八字四柱事实。",
        dimension_ids: ["state"],
      },
      "chart-similarity-intent-1",
    );
  });

  it("rejects the same profile version on both sides", async () => {
    const user = userEvent.setup();
    render(<ChartSimilarityFlow />);

    const right = await screen.findByLabelText("右侧已确认档案");
    await user.selectOptions(right, "version-1");
    await user.click(screen.getByRole("button", { name: /开始比较四柱事实/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "左右两侧必须选择不同的档案版本。",
    );
    expect(api.startChartSimilarityReading).not.toHaveBeenCalled();
  });
});
