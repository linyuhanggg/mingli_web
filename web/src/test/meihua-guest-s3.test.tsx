import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";

const { mockStartMeihuaReading, mockPush } = vi.hoisted(() => ({
  mockStartMeihuaReading: vi.fn(),
  mockPush: vi.fn(),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => "/meihua",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
  startMeihuaReading: mockStartMeihuaReading,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div data-testid="meihua-inline-result">本页梅花盘面 {readingId}</div>
  ),
}));

afterEach(() => {
  cleanup();
  mockStartMeihuaReading.mockReset();
  mockPush.mockReset();
});

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这件事后续如何");
  await user.selectOptions(screen.getByLabelText("判断侧重"), "outcome");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-21T09:30" },
  });
  await user.type(screen.getByLabelText("事件地点"), "上海市");
}

describe("/meihua guest stays on S3", () => {
  it("keeps a successful guest cast on /meihua and does not push history", async () => {
    mockStartMeihuaReading.mockResolvedValue({
      reading_version_id: "mh-guest-1",
    });
    const user = userEvent.setup();
    render(<ProductTaskPage productId="meihua" />);
    await fillShared(user);
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));

    const board = await screen.findByTestId("meihua-inline-result");
    expect(board).toHaveTextContent("mh-guest-1");
    expect(mockStartMeihuaReading).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "梅花工作台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: /梅花/ })).not.toBeInTheDocument();
    expect(screen.queryByText("登录后才能查看历史")).not.toBeInTheDocument();
    expect(screen.queryByText("需要登录才能查看历史")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: /梅花/ })).toBeVisible();
    expect(screen.queryByTestId("meihua-inline-result")).not.toBeInTheDocument();
  });
});
