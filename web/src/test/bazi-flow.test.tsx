import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BaziFlow } from "@/components/bazi-flow";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
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
    startPreviewReading: api.startPreviewReading,
  };
});

const profileVersionId = "22222222-2222-4222-8222-222222222222";

beforeEach(() => {
  navigation.push.mockReset();
  api.listProfiles.mockReset();
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
});

describe("BaziFlow", () => {
  it("states the currently supported narrative scope before submitting", async () => {
    const user = userEvent.setup();
    render(<BaziFlow />);

    await user.selectOptions(await screen.findByLabelText("档案版本"), profileVersionId);
    expect(screen.getByText("当前白话解读范围：事业与工作。")).toBeVisible();
    expect(screen.getByText(/盘面仍展示服务端返回的四柱事实/)).toBeVisible();
    expect(
      screen.queryByRole("radio", { name: "整体概览" }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /开始事业主题概览/ }),
    );

    await waitFor(() => expect(api.startPreviewReading).toHaveBeenCalledTimes(1));
    expect(api.startPreviewReading).toHaveBeenCalledWith(
      expect.objectContaining({
        profile_version_id: profileVersionId,
        dimension_ids: ["career"],
        query: "查看这个档案的事业与工作主题",
      }),
      expect.any(String),
    );
  });
});
