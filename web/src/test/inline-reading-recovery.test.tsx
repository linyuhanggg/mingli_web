import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductTaskExperience } from "@/components/task/product-task-experience";
import type { TaskFormValues } from "@/components/task/product-input-form";
import {
  loadRecoverableReading,
  saveRecoverableReading,
} from "@/lib/reading-recovery";
import { getProductDefinition } from "@/products/catalog";

const taskFormDefaultValues: TaskFormValues = {
  subject: "",
  calendar: "gregorian",
  birthDate: "",
  birthTime: "",
  targetYear: "",
  targetMonth: "",
  targetDate: "",
  unknownTime: false,
  location: "",
  timezone: "Asia/Shanghai",
  gender: "",
  timeStandard: "civil",
  longitude: "",
  latitude: "",
  coordinateSource: "",
  issue: "",
  focus: "",
  eventTime: "",
  timingStart: "",
  timingEnd: "",
  divinationMethod: "coins",
  meihuaCastingMethod: "time",
  meihuaNumber: "",
  meihuaCount: "",
  meihuaUpperTrigram: "乾",
  meihuaLowerTrigram: "坤",
  meihuaMovingLine: "1",
  meihuaSource: "",
  observationMode: "face",
  observationRegion: "forehead",
  observationDescriptor: "region_visible",
  observationVisibility: "full",
  observationUncertainty: "0",
  selectionEventProfile: "business_opening_transaction",
  selectionActions: "开市",
  selectionStart: "",
  selectionEnd: "",
  selectionConstraints: "",
  fengshuiPropertyScope: "residential",
  fengshuiSelectedSchool: "bazhai",
  fengshuiFacingDegrees: "180",
  fengshuiUncertaintyDegrees: "0",
  consent: false,
  photoSelected: false,
  observationNotes: "",
  saveToArchive: false,
  profile: "",
  arts: [],
  preference: "direct",
  lines: ["", "", "", "", "", ""],
};

const api = vi.hoisted(() => ({
  confirmProfileDraft: vi.fn(),
  createProfileDraft: vi.fn(),
  listProfiles: vi.fn(),
  startDaliurenReading: vi.fn(),
  startLiuyaoReading: vi.fn(),
  startMeihuaReading: vi.fn(),
  startPreviewReading: vi.fn(),
  startZiweiReading: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...api,
}));

vi.mock("@/components/task/product-input-form", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/task/product-input-form")>()),
  ProductInputForm: () => <div>input</div>,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({
    initialViewModel,
    readingId,
    onRestart,
    startedAt,
  }: {
    initialViewModel?: { schema_name?: string };
    readingId: string;
    onRestart?: () => void;
    startedAt?: number;
  }) => (
    <section>
      <span>{readingId}</span>
      <span data-testid={`start-projection-${readingId}`}>
        {initialViewModel?.schema_name ?? "none"}
      </span>
      <span data-testid={`started-at-${readingId}`}>{startedAt}</span>
      {onRestart ? (
        <button onClick={onRestart} type="button">
          重试（保留原资料）
        </button>
      ) : null}
    </section>
  ),
}));

vi.mock("@/components/task/bazi-deep-task-flow", () => ({
  BaziDeepTaskFlow: ({
    initialPreviewViewModel,
    previewReadingId,
    onRestart,
    startedAt,
  }: {
    initialPreviewViewModel?: { schema_name?: string };
    previewReadingId: string;
    onRestart?: () => void;
    startedAt?: number;
  }) => (
    <section>
      <span>{previewReadingId}</span>
      <span data-testid={`start-projection-${previewReadingId}`}>
        {initialPreviewViewModel?.schema_name ?? "none"}
      </span>
      <span data-testid={`started-at-${previewReadingId}`}>{startedAt}</span>
      {onRestart ? (
        <button onClick={onRestart} type="button">
          重试（保留原资料）
        </button>
      ) : null}
    </section>
  ),
}));

const PROFILE_VERSION_ID = "22222222-2222-4222-8222-222222222222";
const RESTORED_STARTED_AT = Date.now() - 10_000;
const SERVER_STARTED_AT = Date.now() - 5_000;

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  };
}

afterEach(() => {
  vi.useRealTimers();
});

beforeEach(() => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: memoryStorage(),
  });
  Object.defineProperty(window, "sessionStorage", {
    configurable: true,
    value: memoryStorage(),
  });
  window.localStorage.clear();
  window.sessionStorage.clear();
  for (const mock of Object.values(api)) mock.mockReset();
  api.listProfiles.mockResolvedValue({
    profiles: [
      {
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: PROFILE_VERSION_ID,
        subject_ref: `profile-version:${PROFILE_VERSION_ID}`,
        version: 1,
        display_name: "我自己 · 1994",
        birth_date: "1994-04-30",
        created_at: "2026-08-24T00:00:00Z",
      },
    ],
  });
  api.startPreviewReading.mockResolvedValue({
    reading_version_id: "next-bazi",
    created_at: new Date(SERVER_STARTED_AT).toISOString(),
  });
  api.startZiweiReading.mockResolvedValue({
    reading_version_id: "next-ziwei",
    created_at: new Date(SERVER_STARTED_AT).toISOString(),
  });
  api.startLiuyaoReading.mockResolvedValue({
    reading_version_id: "next-liuyao",
    created_at: new Date(SERVER_STARTED_AT).toISOString(),
  });
  api.startMeihuaReading.mockResolvedValue({
    reading_version_id: "next-meihua",
    created_at: new Date(SERVER_STARTED_AT).toISOString(),
  });
  api.startDaliurenReading.mockResolvedValue({
    reading_version_id: "next-daliuren",
    created_at: new Date(SERVER_STARTED_AT).toISOString(),
  });
});

describe("inline reading recovery", () => {
  it("stores only a versioned, expiring session record and never writes localStorage", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-25T00:00:00Z"));
    saveRecoverableReading("bazi", "old-bazi", {
      profileVersionId: PROFILE_VERSION_ID,
      startedAt: Date.now() - 12_345,
      values: {
        ...taskFormDefaultValues,
        subject: "不应重复保存的受测对象",
        birthDate: "1994-04-30",
        issue: "看看事业",
        targetYear: "2028",
      },
    });

    expect(window.localStorage).toHaveLength(0);
    expect(window.sessionStorage).toHaveLength(1);
    const raw = window.sessionStorage.getItem(window.sessionStorage.key(0) ?? "");
    expect(raw).not.toBeNull();
    const record = JSON.parse(raw ?? "{}") as Record<string, unknown>;
    expect(record.version).toBe(3);
    expect(record.started_at).toBe(Date.now() - 12_345);
    expect(record.expires_at).toBe(Date.now() + 30 * 60 * 1000);
    expect(raw).toContain("看看事业");
    expect(raw).not.toContain("不应重复保存的受测对象");
    expect(raw).not.toContain("1994-04-30");
  });

  it("drops an expired session record instead of replaying stale private input", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-25T00:00:00Z"));
    saveRecoverableReading("meihua", "old-meihua", {
      startedAt: Date.now(),
      values: {
        ...taskFormDefaultValues,
        issue: "是否继续",
        focus: "outcome",
        eventTime: "2026-08-25T08:00",
        location: "上海市",
      },
    });
    vi.setSystemTime(new Date("2026-08-25T00:30:00.001Z"));

    expect(loadRecoverableReading("meihua")).toBeNull();
    expect(window.sessionStorage).toHaveLength(0);
  });

  it("fails closed when session storage rejects reads and cleanup", () => {
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: {
        getItem: () => {
          throw new DOMException("blocked", "SecurityError");
        },
        removeItem: () => {
          throw new DOMException("blocked", "SecurityError");
        },
      },
    });

    expect(loadRecoverableReading("bazi")).toBeNull();
  });

  it.each([
    {
      productId: "bazi" as const,
      oldId: "old-bazi",
      nextId: "next-bazi",
      profileVersionId: PROFILE_VERSION_ID,
      values: { issue: "看看事业", targetYear: "2028" },
      start: api.startPreviewReading,
      expected: { profile_version_id: PROFILE_VERSION_ID, query: "看看事业", target_year: 2028 },
    },
    {
      productId: "ziwei" as const,
      oldId: "old-ziwei",
      nextId: "next-ziwei",
      profileVersionId: PROFILE_VERSION_ID,
      values: { issue: "看看命盘", targetMonth: "2028-03" },
      start: api.startZiweiReading,
      expected: { profile_version_id: PROFILE_VERSION_ID, query: "看看命盘", target_month: "2028-03" },
    },
    {
      productId: "liuyao" as const,
      oldId: "old-liuyao",
      nextId: "next-liuyao",
      values: {
        issue: "项目能否按期完成",
        focus: "manual",
        eventTime: "2026-08-25T08:00",
        timezone: "Asia/Shanghai",
        location: "上海市",
        lines: ["young-yang", "young-yin", "old-yang", "young-yin", "old-yin", "young-yang"],
      },
      start: api.startLiuyaoReading,
      expected: { query: "项目能否按期完成", location: "上海市", cast: [7, 8, 9, 8, 6, 7] },
    },
    {
      productId: "meihua" as const,
      oldId: "old-meihua",
      nextId: "next-meihua",
      values: {
        issue: "是否继续推进",
        focus: "outcome",
        eventTime: "2026-08-25T08:00",
        timezone: "Asia/Shanghai",
        location: "上海市",
        timeStandard: "civil",
        meihuaCastingMethod: "supplied_number",
        meihuaNumber: "18",
        meihuaSource: "用户输入",
      },
      start: api.startMeihuaReading,
      expected: { query: "是否继续推进", number: 18, location: "上海市" },
    },
    {
      productId: "daliuren" as const,
      oldId: "old-daliuren",
      nextId: "next-daliuren",
      values: {
        issue: "何时有回应",
        focus: "timing",
        eventTime: "2026-08-25T08:00",
        timezone: "Asia/Shanghai",
        location: "上海市",
        timeStandard: "civil",
        timingStart: "2026-08-26",
        timingEnd: "2026-09-02",
      },
      start: api.startDaliurenReading,
      expected: {
        query: "何时有回应",
        location: "上海市",
        timing_start: "2026-08-26",
        timing_end: "2026-09-02",
      },
    },
  ])(
    "rebuilds a new $productId task through its existing submit API after refresh",
    async ({ productId, oldId, nextId, profileVersionId, values, start, expected }) => {
      saveRecoverableReading(productId, oldId, {
        ...(profileVersionId ? { profileVersionId } : {}),
        startedAt: RESTORED_STARTED_AT,
        values: { ...taskFormDefaultValues, ...values },
      });

      render(<ProductTaskExperience product={getProductDefinition(productId)} />);

      expect(await screen.findByText(oldId)).toBeVisible();
      expect(screen.getByTestId(`started-at-${oldId}`)).toHaveTextContent(
        String(RESTORED_STARTED_AT),
      );
      fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));

      await waitFor(() => expect(start).toHaveBeenCalledTimes(1));
      expect(start).toHaveBeenCalledWith(expect.objectContaining(expected), expect.any(String));
      expect(await screen.findByText(nextId)).toBeVisible();
      expect(loadRecoverableReading(productId)?.readingVersionId).toBe(nextId);
      expect(loadRecoverableReading(productId)?.startedAt).toBe(
        SERVER_STARTED_AT,
      );
      expect(api.createProfileDraft).not.toHaveBeenCalled();
      expect(api.confirmProfileDraft).not.toHaveBeenCalled();
    },
  );

  it("creates a new Bazi Reading and a fresh idempotency intent on every restart", async () => {
    saveRecoverableReading("bazi", "old-bazi", {
      profileVersionId: PROFILE_VERSION_ID,
      startedAt: RESTORED_STARTED_AT,
      values: {
        ...taskFormDefaultValues,
        issue: "看看事业",
        targetYear: "2028",
      },
    });
    api.startPreviewReading
      .mockResolvedValueOnce({
        reading_version_id: "next-bazi",
        created_at: new Date(SERVER_STARTED_AT).toISOString(),
      })
      .mockResolvedValueOnce({
        reading_version_id: "newest-bazi",
        created_at: new Date(SERVER_STARTED_AT + 1_000).toISOString(),
      });

    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);

    expect(await screen.findByText("old-bazi")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));
    expect(await screen.findByText("next-bazi")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));
    expect(await screen.findByText("newest-bazi")).toBeVisible();

    expect(api.startPreviewReading).toHaveBeenCalledTimes(2);
    const firstIntent = api.startPreviewReading.mock.calls[0]?.[1];
    const secondIntent = api.startPreviewReading.mock.calls[1]?.[1];
    expect(firstIntent).toEqual(expect.any(String));
    expect(secondIntent).toEqual(expect.any(String));
    expect(secondIntent).not.toBe(firstIntent);
    expect(loadRecoverableReading("bazi")?.readingVersionId).toBe("newest-bazi");
  });

  it.each([
    {
      productId: "bazi" as const,
      readingId: "next-bazi",
      start: api.startPreviewReading,
      values: { issue: "看看事业", targetYear: "2028" },
      profileVersionId: PROFILE_VERSION_ID,
    },
    {
      productId: "meihua" as const,
      readingId: "next-meihua",
      start: api.startMeihuaReading,
      values: {
        issue: "是否继续推进",
        focus: "outcome",
        eventTime: "2026-08-25T08:00",
        timezone: "Asia/Shanghai",
        location: "上海市",
        meihuaCastingMethod: "supplied_number",
        meihuaNumber: "18",
        meihuaSource: "用户输入",
      },
    },
  ])(
    "passes the $productId POST ViewModel into the first visible result",
    async ({ productId, readingId, start, values, profileVersionId }) => {
      saveRecoverableReading(productId, `old-${productId}`, {
        ...(profileVersionId ? { profileVersionId } : {}),
        startedAt: RESTORED_STARTED_AT,
        values: { ...taskFormDefaultValues, ...values },
      });
      start.mockResolvedValueOnce({
        reading_version_id: readingId,
        created_at: new Date(SERVER_STARTED_AT).toISOString(),
        status: "prepared",
        view_model: { schema_name: `${productId}_chart` },
      });

      render(<ProductTaskExperience product={getProductDefinition(productId)} />);
      expect(await screen.findByText(`old-${productId}`)).toBeVisible();
      fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));

      expect(await screen.findByText(readingId)).toBeVisible();
      expect(screen.getByTestId(`start-projection-${readingId}`)).toHaveTextContent(
        `${productId}_chart`,
      );
    },
  );

  it("does not render an untrusted Daliuren POST projection before capability gating", async () => {
    saveRecoverableReading("daliuren", "old-daliuren", {
      startedAt: RESTORED_STARTED_AT,
      values: {
        ...taskFormDefaultValues,
        issue: "何时有回应",
        focus: "timing",
        eventTime: "2026-08-25T08:00",
        timezone: "Asia/Shanghai",
        location: "上海市",
        timingStart: "2026-08-26",
        timingEnd: "2026-09-02",
      },
    });
    api.startDaliurenReading.mockResolvedValueOnce({
      reading_version_id: "next-daliuren",
      created_at: new Date(SERVER_STARTED_AT).toISOString(),
      status: "prepared",
      view_model: { schema_name: "daliuren_chart" },
    });

    render(<ProductTaskExperience product={getProductDefinition("daliuren")} />);
    expect(await screen.findByText("old-daliuren")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));

    expect(await screen.findByText("next-daliuren")).toBeVisible();
    expect(screen.getByTestId("start-projection-next-daliuren")).toHaveTextContent(
      "none",
    );
  });
});
