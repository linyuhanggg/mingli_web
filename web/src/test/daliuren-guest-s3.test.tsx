import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";

const { mockStartDaliurenReading, mockPush } = vi.hoisted(() => ({
  mockStartDaliurenReading: vi.fn(),
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
  usePathname: () => "/daliuren",
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
  startDaliurenReading: mockStartDaliurenReading,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div data-testid="daliuren-inline-result">本页大六壬盘面 {readingId}</div>
  ),
}));

afterEach(() => {
  cleanup();
  mockStartDaliurenReading.mockReset();
  mockPush.mockReset();
});

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这件事后续如何");
  await user.selectOptions(screen.getByLabelText("判断侧重"), "progress");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-22T19:00" },
  });
  await user.type(screen.getByLabelText("事件地点"), "莆田市");
}

describe("/daliuren guest stays on S3", () => {
  it("keeps a successful guest cast on /daliuren and does not push history", async () => {
    mockStartDaliurenReading.mockResolvedValue({
      reading_version_id: "dl-guest-1",
    });
    const user = userEvent.setup();
    render(<ProductTaskPage productId="daliuren" />);
    await fillShared(user);
    await user.click(screen.getByRole("button", { name: /立即起课/ }));

    const board = await screen.findByTestId("daliuren-inline-result");
    expect(board).toHaveTextContent("dl-guest-1");
    expect(screen.getByRole("status", { name: "大六壬盘面" })).toBeVisible();
    expect(screen.getByText("盘面留在本页。登录只用于保存、历史和深读。")).toBeVisible();
    expect(mockStartDaliurenReading).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "大六壬工作台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: /大六壬/ })).not.toBeInTheDocument();
    expect(screen.queryByText("登录后才能查看历史")).not.toBeInTheDocument();
    expect(screen.queryByText("需要登录才能查看历史")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: /大六壬/ })).toBeVisible();
    expect(screen.queryByTestId("daliuren-inline-result")).not.toBeInTheDocument();
  });
});
