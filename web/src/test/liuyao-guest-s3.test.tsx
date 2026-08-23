import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";

const { mockStartLiuyaoReading, mockPush } = vi.hoisted(() => ({
  mockStartLiuyaoReading: vi.fn(),
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
  usePathname: () => "/liuyao",
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
  startLiuyaoReading: mockStartLiuyaoReading,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div data-testid="liuyao-inline-result">本页六爻盘面 {readingId}</div>
  ),
}));

afterEach(() => {
  cleanup();
  mockStartLiuyaoReading.mockReset();
  mockPush.mockReset();
});

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这笔合作能否推进");
  await user.selectOptions(screen.getByLabelText("起卦方式"), "coins");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-22T19:00" },
  });
  await user.type(screen.getByLabelText("事件地点"), "莆田市");
}

async function fillLines(user: ReturnType<typeof userEvent.setup>) {
  const lineGroups = screen.getAllByRole("group", { name: /第 \d 次/ });
  for (const group of lineGroups) {
    await user.click(within(group).getByRole("radio", { name: /少阳/ }));
  }
}

describe("/liuyao guest stays on S3", () => {
  it("keeps a successful guest cast on /liuyao and does not push history", async () => {
    mockStartLiuyaoReading.mockResolvedValue({
      reading_version_id: "ly-guest-1",
    });
    const user = userEvent.setup();
    render(<ProductTaskPage productId="liuyao" />);
    await fillShared(user);
    await fillLines(user);
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));
    await waitFor(() => expect(mockStartLiuyaoReading).toHaveBeenCalledTimes(1));

    const board = await screen.findByTestId("liuyao-inline-result");
    expect(board).toHaveTextContent("ly-guest-1");
    expect(screen.getByRole("status", { name: "六爻盘面" })).toBeVisible();
    expect(screen.getByText("盘面留在本页。登录只用于保存、历史和深读。")).toBeVisible();
    expect(mockStartLiuyaoReading).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "六爻工作台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: /六爻/ })).not.toBeInTheDocument();
    expect(screen.queryByText("登录后才能查看历史")).not.toBeInTheDocument();
    expect(screen.queryByText("需要登录才能查看历史")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: /六爻/ })).toBeVisible();
    expect(screen.queryByTestId("liuyao-inline-result")).not.toBeInTheDocument();
  });
});
