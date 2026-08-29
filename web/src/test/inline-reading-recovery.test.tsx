import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductTaskExperience } from "@/components/task/product-task-experience";
import type { TaskFormValues } from "@/components/task/product-input-form";
import {
  loadRecoverableReading,
  saveRecoverableReading,
} from "@/lib/reading-recovery";
import { getProductDefinition } from "@/products/catalog";

const navigation = vi.hoisted(() => ({
  pathname: "/ziwei",
  replace: vi.fn(),
  search: "",
}));
const ownerEvents = vi.hoisted(() => [] as string[]);
const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
  startLiuyaoReading: vi.fn(),
  startZiweiReading: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => ({
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    replace: navigation.replace,
  }),
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  listProfiles: api.listProfiles,
  startLiuyaoReading: api.startLiuyaoReading,
  startZiweiReading: api.startZiweiReading,
}));

vi.mock("@/components/task/product-input-form", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/task/product-input-form")>()),
  ProductInputForm: () => <div>input</div>,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({
    onRestart,
    readingId,
    startedAt,
  }: {
    onRestart?: () => void;
    readingId: string;
    startedAt?: number;
  }) => {
    useEffect(() => {
      ownerEvents.push(`mount:${readingId}`);
      return () => {
        ownerEvents.push(`unmount:${readingId}`);
      };
    }, [readingId]);
    return (
      <section aria-label={`reading:${readingId}`}>
        <span>{readingId}</span>
        <span data-testid={`started-at-${readingId}`}>{startedAt}</span>
        {onRestart ? (
          <button onClick={onRestart} type="button">
            重试（保留原资料）
          </button>
        ) : null}
      </section>
    );
  },
}));

vi.mock("@/components/task/bazi-deep-task-flow", () => ({
  BaziDeepTaskFlow: () => null,
  baziPreviewRestoreHref: () => "/bazi",
  readBaziPreviewReadingId: () => null,
}));

const PROFILE_VERSION_ID = "22222222-2222-4222-8222-222222222222";
const STARTED_AT = Date.parse("2026-08-29T12:00:00Z");

const taskValues: TaskFormValues = {
  subject: "不应持久化的姓名",
  calendar: "gregorian",
  birthDate: "1990-01-02",
  birthTime: "08:30",
  targetYear: "2028",
  targetMonth: "2028-03",
  targetDate: "",
  unknownTime: false,
  location: "上海市",
  timezone: "Asia/Shanghai",
  gender: "female",
  timeStandard: "civil",
  longitude: "",
  latitude: "",
  coordinateSource: "",
  issue: "看看这件事",
  focus: "manual",
  eventTime: "2026-08-29T20:00",
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
  lines: ["young-yang", "young-yin", "old-yang", "young-yin", "old-yin", "young-yang"],
};

beforeEach(() => {
  window.sessionStorage.clear();
  ownerEvents.length = 0;
  navigation.pathname = "/ziwei";
  navigation.search = "";
  navigation.replace.mockReset();
  api.listProfiles.mockReset().mockResolvedValue({
    profiles: [
      {
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: PROFILE_VERSION_ID,
        subject_ref: `profile-version:${PROFILE_VERSION_ID}`,
        version: 1,
        created_at: "2026-08-29T00:00:00Z",
      },
    ],
  });
  api.startLiuyaoReading.mockReset();
  api.startZiweiReading.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Ziwei and Liuyao inline reading recovery", () => {
  it("stores only the art-specific restart fields in session storage", () => {
    saveRecoverableReading("ziwei", "old-ziwei", {
      profileVersionId: PROFILE_VERSION_ID,
      startedAt: STARTED_AT,
      values: taskValues,
    });

    const recovery = loadRecoverableReading("ziwei", "old-ziwei");
    expect(recovery).toMatchObject({
      readingVersionId: "old-ziwei",
      startedAt: STARTED_AT,
      submission: {
        profileVersionId: PROFILE_VERSION_ID,
        values: {
          issue: "看看这件事",
          targetMonth: "2028-03",
          targetYear: "2028",
        },
      },
    });
    const raw = window.sessionStorage.getItem("mingli.inline-reading.v1.ziwei") ?? "";
    expect(raw).not.toContain("不应持久化的姓名");
    expect(raw).not.toContain("1990-01-02");
    expect(loadRecoverableReading("ziwei", "different-id")).toBeNull();
    expect(loadRecoverableReading("meihua", "old-ziwei")).toBeNull();
  });

  it("restores Ziwei from URL plus session and aborts the old owner before restart resolves", async () => {
    navigation.pathname = "/ziwei";
    navigation.search = "reading=old-ziwei";
    saveRecoverableReading("ziwei", "old-ziwei", {
      profileVersionId: PROFILE_VERSION_ID,
      startedAt: STARTED_AT,
      values: taskValues,
    });
    let releaseStart!: (value: { reading_version_id: string; created_at: string }) => void;
    api.startZiweiReading.mockReturnValue(new Promise((resolve) => {
      releaseStart = resolve;
    }));

    render(<ProductTaskExperience product={getProductDefinition("ziwei")} />);

    expect(await screen.findByText("old-ziwei")).toBeVisible();
    expect(screen.getByTestId("started-at-old-ziwei")).toHaveTextContent(String(STARTED_AT));
    fireEvent.click(screen.getByRole("button", { name: "重试（保留原资料）" }));
    await waitFor(() => expect(ownerEvents).toContain("unmount:old-ziwei"));
    expect(api.startZiweiReading).toHaveBeenCalledWith(
      expect.objectContaining({
        profile_version_id: PROFILE_VERSION_ID,
        query: "看看这件事",
        target_month: "2028-03",
      }),
      expect.any(String),
    );

    releaseStart({
      reading_version_id: "next-ziwei",
      created_at: "2026-08-29T12:01:00Z",
    });
    expect(await screen.findByText("next-ziwei")).toBeVisible();
    expect(navigation.replace).toHaveBeenLastCalledWith("/ziwei?reading=next-ziwei");
    expect(loadRecoverableReading("ziwei", "next-ziwei")?.startedAt).toBe(
      Date.parse("2026-08-29T12:01:00Z"),
    );
  });

  it("restores Liuyao and clears both URL and session on explicit return", async () => {
    navigation.pathname = "/liuyao";
    navigation.search = "reading=old-liuyao";
    saveRecoverableReading("liuyao", "old-liuyao", {
      startedAt: STARTED_AT,
      values: taskValues,
    });

    render(<ProductTaskExperience product={getProductDefinition("liuyao")} />);

    expect(await screen.findByText("old-liuyao")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "返回录入" }));

    expect(await screen.findByText("input")).toBeVisible();
    expect(loadRecoverableReading("liuyao", "old-liuyao")).toBeNull();
    expect(navigation.replace).toHaveBeenLastCalledWith("/liuyao");
    expect(ownerEvents).toContain("unmount:old-liuyao");
  });
});
