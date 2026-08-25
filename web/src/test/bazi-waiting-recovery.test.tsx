import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductTaskExperience } from "@/components/task/product-task-experience";
import { loadRecoverableReading } from "@/lib/reading-recovery";
import { getProductDefinition } from "@/products/catalog";

const PROFILE_VERSION_ID = "22222222-2222-4222-8222-222222222222";
const pollTimes = new Map<string, number[]>();

const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
  startPreviewReading: vi.fn(),
}));

const formValues = vi.hoisted(() => ({
  subject: "虚构用户",
  birthDate: "1990-05-06",
  birthTime: "08:30",
  timezone: "Asia/Shanghai",
  location: "上海市",
  gender: "female",
  timeStandard: "civil",
  longitude: "",
  latitude: "",
  coordinateSource: "",
  issue: "看看事业",
  targetYear: "2028",
  targetMonth: "",
  targetDate: "",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...api,
}));

vi.mock("@/components/task/product-input-form", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/task/product-input-form")>()),
  ProductInputForm: ({
    onConfirm,
    selectedProfileVersionId,
  }: {
    onConfirm: (values: typeof formValues) => void;
    selectedProfileVersionId: string;
  }) => (
    <section>
      <span>{selectedProfileVersionId ? "档案已就绪" : "正在读取档案"}</span>
      <button
        disabled={!selectedProfileVersionId}
        onClick={() => onConfirm(formValues)}
        type="button"
      >
        免费排盘
      </button>
    </section>
  ),
}));

function readingSummary(readingId: string, createdAt: string) {
  return {
    reading_version_id: readingId,
    reading_root_id: `${readingId}-root`,
    profile_version_id: PROFILE_VERSION_ID,
    capability_id: "bazi",
    product_id: "bazi",
    runtime_capability_ids: ["bazi"],
    version: 1,
    status: "input_ready" as const,
    object_id: "natal",
    dimension_ids: ["career"],
    horizon: { kind_id: "life", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: createdAt,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-08-25T00:00:00Z"));
  window.sessionStorage.clear();
  pollTimes.clear();
  api.listProfiles.mockReset();
  api.startPreviewReading.mockReset();
  api.listProfiles.mockResolvedValue({
    profiles: [
      {
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: PROFILE_VERSION_ID,
        subject_ref: `profile-version:${PROFILE_VERSION_ID}`,
        version: 1,
        display_name: "虚构用户",
        birth_date: "1990-05-06",
        created_at: "2026-08-24T00:00:00Z",
      },
    ],
  });
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (url) => {
    const readingId = String(url).split("/").at(-1) ?? "";
    pollTimes.set(readingId, [...(pollTimes.get(readingId) ?? []), Date.now()]);
    return new Response(
      JSON.stringify(
        readingSummary(
          readingId,
          readingId === "bazi-reading-1"
            ? "2026-08-25T00:00:00Z"
            : "2026-08-25T00:01:00Z",
        ),
      ),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }));
  api.startPreviewReading
    .mockResolvedValueOnce(readingSummary("bazi-reading-1", "2026-08-25T00:00:00Z"))
    .mockImplementationOnce(async () =>
      readingSummary("bazi-reading-2", new Date(Date.now()).toISOString()),
    );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("real Bazi workbench waiting recovery", () => {
  it("uses shared waiting thresholds and restarts with a new Reading and intent", async () => {
    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText("档案已就绪")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "免费排盘" }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByRole("status")).toHaveTextContent("正在为你排盘");
    expect(pollTimes.get("bazi-reading-1")).toEqual([Date.parse("2026-08-25T00:00:00Z")]);

    await act(async () => vi.advanceTimersByTimeAsync(700));
    expect(pollTimes.get("bazi-reading-1")?.map((time) => time % 60_000)).toEqual([0, 1_000]);
    await act(async () => vi.advanceTimersByTimeAsync(1_999));
    expect(pollTimes.get("bazi-reading-1")).toHaveLength(2);
    await act(async () => vi.advanceTimersByTimeAsync(1));
    await act(async () => vi.advanceTimersByTimeAsync(3_999));
    expect(pollTimes.get("bazi-reading-1")).toHaveLength(3);
    await act(async () => vi.advanceTimersByTimeAsync(1));
    await act(async () => vi.advanceTimersByTimeAsync(8_000));
    expect(pollTimes.get("bazi-reading-1")?.slice(0, 6).map((time) => time % 60_000)).toEqual([
      0,
      1_000,
      3_000,
      7_000,
      11_000,
      15_000,
    ]);
    expect(screen.getByRole("status")).toHaveTextContent("仍在认真排盘");
    expect(screen.getByRole("link", { name: "稍后查看" })).toBeVisible();

    await act(async () => vi.advanceTimersByTimeAsync(45_000));
    expect(screen.getByRole("status")).toHaveTextContent("这次排盘比平时久");
    fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(api.startPreviewReading).toHaveBeenCalledTimes(2);
    const firstIntent = api.startPreviewReading.mock.calls[0]?.[1];
    const secondIntent = api.startPreviewReading.mock.calls[1]?.[1];
    expect(firstIntent).toEqual(expect.any(String));
    expect(secondIntent).toEqual(expect.any(String));
    expect(secondIntent).not.toBe(firstIntent);
    expect(loadRecoverableReading("bazi")?.readingVersionId).toBe("bazi-reading-2");
    const oldReadingCount = pollTimes.get("bazi-reading-1")?.length;
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(pollTimes.get("bazi-reading-2")).toHaveLength(1);
    await act(async () => vi.advanceTimersByTimeAsync(7_000));
    expect(pollTimes.get("bazi-reading-1")).toHaveLength(oldReadingCount ?? 0);
    expect(pollTimes.get("bazi-reading-2")?.map((time) => time - 60_000)).toEqual([
      Date.parse("2026-08-25T00:00:00Z"),
      Date.parse("2026-08-25T00:00:01Z"),
      Date.parse("2026-08-25T00:00:03Z"),
      Date.parse("2026-08-25T00:00:07Z"),
    ]);
  });
});
