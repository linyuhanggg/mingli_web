import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockStartZiweiReading = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());
const mockRouterPush = vi.hoisted(() => vi.fn());
const mockRouterReplace = vi.hoisted(() => vi.fn());
const mockNavigation = vi.hoisted(() => ({
  pathname: "/bazi",
  searchParams: new URLSearchParams(),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: mockRouterPush, replace: mockRouterReplace }),
  usePathname: () => mockNavigation.pathname,
  useSearchParams: () => mockNavigation.searchParams,
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  startPreviewReading: mockStartPreviewReading,
  startZiweiReading: mockStartZiweiReading,
  listProfiles: mockListProfiles,
}));

import { ProductTaskExperience } from "@/components/task/product-task-experience";
import { ApiError } from "@/lib/api";
import {
  consumePendingStartTask,
  destinationAfterLogin,
  loadPendingStartTask,
  loginContinueHref,
  PENDING_START_STORAGE_FAILURE_CODE,
  persistPendingStartTask,
  safeContinuePath,
} from "@/lib/login-continue";
import { getProductDefinition } from "@/products/catalog";

const profileVersionId = "11111111-1111-4111-8111-111111111111";
const resumedProfileVersionId = "22222222-2222-4222-8222-222222222222";
const pendingStartReadError = "无法恢复登录前的排盘资料";
const pendingStartWriteError = "无法保存登录续接资料，请允许本网站使用会话存储后重试。";
const nativeSessionStorage = window.sessionStorage;
const nativeSessionStorageDescriptor = Object.getOwnPropertyDescriptor(
  window,
  "sessionStorage",
);

function installSessionStorage(overrides: Partial<Storage>) {
  const replacement: Storage = {
    get length() {
      return nativeSessionStorage.length;
    },
    clear: () => nativeSessionStorage.clear(),
    getItem: (key) => nativeSessionStorage.getItem(key),
    key: (index) => nativeSessionStorage.key(index),
    removeItem: (key) => nativeSessionStorage.removeItem(key),
    setItem: (key, value) => nativeSessionStorage.setItem(key, value),
    ...overrides,
  };
  Object.defineProperty(window, "sessionStorage", {
    configurable: true,
    value: replacement,
  });
}

function restoreSessionStorage() {
  if (nativeSessionStorageDescriptor) {
    Object.defineProperty(window, "sessionStorage", nativeSessionStorageDescriptor);
  }
}

afterEach(() => {
  vi.useRealTimers();
  restoreSessionStorage();
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  mockNavigation.pathname = "/bazi";
  mockNavigation.searchParams = new URLSearchParams();
  window.sessionStorage.clear();
  mockRouterPush.mockReset();
  mockRouterReplace.mockReset();
  mockListProfiles.mockReset().mockResolvedValue({
    profiles: [{
      profile_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      profile_version_id: profileVersionId,
      subject_ref: `profile-version:${profileVersionId}`,
      version: 1,
      display_name: "续接测试档案",
      created_at: "2026-08-27T00:00:00Z",
    }],
  });
  mockCreateProfileDraft.mockReset();
  mockConfirmProfileDraft.mockReset();
  mockStartPreviewReading.mockReset().mockRejectedValue(
    new ApiError("Daily cap", 429, undefined, "guest_daily_reading_limit"),
  );
  mockStartZiweiReading.mockReset().mockRejectedValue(
    new ApiError("Daily cap", 429, undefined, "guest_daily_reading_limit"),
  );
});

describe("safeContinuePath", () => {
  it("keeps same-origin relative destinations", () => {
    expect(safeContinuePath("/account")).toBe("/account");
    expect(safeContinuePath("/app/readings/abc?tab=chart")).toBe(
      "/app/readings/abc?tab=chart",
    );
  });

  it("rejects protocol-relative and absolute URLs", () => {
    expect(safeContinuePath("//evil.example")).toBe("/account");
    expect(safeContinuePath("https://evil.example/")).toBe("/account");
    expect(safeContinuePath("/https://evil.example")).toBe("/account");
  });

  it("rejects backslash authority payloads after URLSearchParams decoding", () => {
    const decoded = new URLSearchParams("next=%2F%5Cevil.example").get("next");
    expect(decoded).toBe("/\\evil.example");
    expect(safeContinuePath(decoded)).toBe("/account");
    expect(safeContinuePath("/\\evil.example", "/workbench")).toBe("/workbench");
  });

  it("rejects control characters in the destination", () => {
    expect(safeContinuePath("/account\n/evil")).toBe("/account");
    expect(safeContinuePath("/account\u0000")).toBe("/account");
  });

  it("falls back when the candidate is empty", () => {
    expect(safeContinuePath(null)).toBe("/account");
    expect(safeContinuePath("")).toBe("/account");
  });
});

describe("loginContinueHref", () => {
  it("puts the idempotency key on the validated next destination, not the login page", () => {
    expect(loginContinueHref("/liuyao", "", "intent-1")).toBe(
      "/auth/login?next=%2Fliuyao%3Fidempotency_key%3Dintent-1",
    );
    expect(loginContinueHref("/bazi", "?tab=chart", "intent-2")).toBe(
      "/auth/login?next=%2Fbazi%3Ftab%3Dchart%26idempotency_key%3Dintent-2",
    );
  });
});

describe("destinationAfterLogin", () => {
  it("uses the next query when it is a safe relative path", () => {
    window.history.replaceState({}, "", "/auth/login?next=%2Fworkbench");
    expect(destinationAfterLogin()).toBe("/workbench");
  });

  it("keeps a destination that already carries the idempotency key", () => {
    window.history.replaceState(
      {},
      "",
      "/auth/login?next=%2Fliuyao%3Fidempotency_key%3Dintent-1",
    );
    expect(destinationAfterLogin()).toBe("/liuyao?idempotency_key=intent-1");
  });

  it("merges a sibling login-page key into the destination for older links", () => {
    window.history.replaceState(
      {},
      "",
      "/auth/login?next=%2Fliuyao&idempotency_key=intent-1",
    );
    expect(destinationAfterLogin()).toBe("/liuyao?idempotency_key=intent-1");
  });

  it("falls back when next uses a backslash as an authority separator", () => {
    window.history.replaceState({}, "", "/auth/login?next=%2F%5Cevil.example");
    expect(destinationAfterLogin()).toBe("/account");
  });
});

describe("pending start task storage", () => {
  it("round-trips form values keyed by the idempotency token", () => {
    expect(persistPendingStartTask("intent-1", {
      productId: "liuyao",
      fingerprint: "{\"product\":\"liuyao\"}",
      values: { question: "此问事业", hexagram: "111111" },
    })).toBeNull();
    expect(loadPendingStartTask("intent-1")).toEqual({
      productId: "liuyao",
      fingerprint: "{\"product\":\"liuyao\"}",
      values: { question: "此问事业", hexagram: "111111" },
    });
    expect(loadPendingStartTask("missing")).toBeNull();
  });

  it("consumes both storage copies once and remains safe when repeated", () => {
    expect(persistPendingStartTask("intent-consume", {
      productId: "bazi",
      fingerprint: "{\"product\":\"bazi\"}",
      values: { subject: "本人" },
    })).toBeNull();
    expect(window.sessionStorage.getItem("mingli.pending-start:intent-consume")).not.toBeNull();

    expect(consumePendingStartTask("intent-consume")).toBeNull();
    expect(window.sessionStorage.getItem("mingli.pending-start:intent-consume")).toBeNull();
    expect(loadPendingStartTask("intent-consume")).toBeNull();
    expect(consumePendingStartTask("intent-consume")).toBeNull();
  });
});

describe("ProductTaskExperience pending start storage failures", () => {
  it.each([
    ["SecurityError", "SecurityError"],
    ["quota error", "QuotaExceededError"],
  ])("fails closed when sessionStorage.setItem throws %s", async (_label, errorName) => {
    installSessionStorage({
      setItem: () => {
        throw new DOMException("storage unavailable", errorName);
      },
    });
    const user = userEvent.setup();

    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(profileSelect).toHaveValue(profileVersionId));
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));

    expect(await screen.findByRole("alert", { name: pendingStartWriteError })).toBeVisible();
    expect(screen.getByRole("button", { name: "重试" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "登录后继续" })).not.toBeInTheDocument();
    expect(mockRouterPush).not.toHaveBeenCalled();
    expect(mockRouterReplace).not.toHaveBeenCalled();

    const intentKey = mockStartPreviewReading.mock.calls[0]?.[1] as string;
    expect(intentKey).toBeTruthy();
    expect(loadPendingStartTask(intentKey)).toBeNull();
  });

  it("renders a recoverable error instead of an empty form when sessionStorage.getItem throws", async () => {
    const resumeKey = "resume-storage-read-failure";
    mockNavigation.searchParams = new URLSearchParams({ idempotency_key: resumeKey });
    installSessionStorage({
      getItem: () => {
        throw new DOMException("storage blocked", "SecurityError");
      },
    });
    expect(loadPendingStartTask(resumeKey)).toEqual({
      code: PENDING_START_STORAGE_FAILURE_CODE,
      operation: "read",
    });
    const user = userEvent.setup();

    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    expect(await screen.findByRole("alert", { name: pendingStartReadError })).toBeVisible();
    expect(screen.queryByRole("form", { name: "八字任务输入" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "登录后继续" })).not.toBeInTheDocument();
    expect(mockRouterPush).not.toHaveBeenCalled();
    expect(mockRouterReplace).not.toHaveBeenCalled();

    restoreSessionStorage();
    await user.click(screen.getByRole("button", { name: "重试恢复" }));
    expect(await screen.findByRole("form", { name: "八字任务输入" })).toBeVisible();
  });
});

describe("ProductTaskExperience resumed profile selection", () => {
  const profiles = [
    {
      profile_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      profile_version_id: profileVersionId,
      subject_ref: `profile-version:${profileVersionId}`,
      version: 1,
      display_name: "路由档案 A",
      created_at: "2026-08-27T00:00:00Z",
    },
    {
      profile_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      profile_version_id: resumedProfileVersionId,
      subject_ref: `profile-version:${resumedProfileVersionId}`,
      version: 1,
      display_name: "续接档案 B",
      created_at: "2026-08-27T00:01:00Z",
    },
  ];

  const chartContinuations = [
    { productId: "bazi", pathname: "/bazi", startMock: mockStartPreviewReading },
    { productId: "ziwei", pathname: "/ziwei", startMock: mockStartZiweiReading },
  ] as const;

  async function prepareResumedChart(
    productId: "bazi" | "ziwei",
    pathname: string,
    startMock: typeof mockStartPreviewReading,
  ) {
    mockNavigation.pathname = pathname;
    const user = userEvent.setup();
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition(productId),
    }));

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(profileSelect).toHaveValue(profileVersionId));
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    expect(await screen.findByRole("link", { name: "登录后继续" })).toBeVisible();

    const resumeKey = startMock.mock.calls[0]?.[1] as string;
    expect(loadPendingStartTask(resumeKey)).not.toBeNull();
    cleanup();

    mockNavigation.searchParams = new URLSearchParams({ idempotency_key: resumeKey });
    return resumeKey;
  }

  it.each(chartContinuations)(
    "keeps the $productId continuation and key after a late success following return",
    async ({ productId, pathname, startMock }) => {
      const resumeKey = await prepareResumedChart(productId, pathname, startMock);
      let releaseStart!: (value: { reading_version_id: string }) => void;
      startMock.mockReturnValueOnce(new Promise((resolve) => {
        releaseStart = resolve;
      }));
      render(createElement(ProductTaskExperience, {
        product: getProductDefinition(productId),
      }));
      const resumedProfileSelect = await screen.findByRole("combobox", {
        name: "排盘资料",
      });
      await waitFor(() => expect(resumedProfileSelect).toHaveValue(profileVersionId));

      vi.useFakeTimers();
      fireEvent.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(startMock).toHaveBeenCalledTimes(2);
      act(() => vi.advanceTimersByTime(15_000));
      fireEvent.click(screen.getByRole("button", { name: "返回录入" }));

      await act(async () => {
        releaseStart({ reading_version_id: `late-${productId}-return` });
        await Promise.resolve();
      });
      expect(loadPendingStartTask(resumeKey)).not.toBeNull();

      startMock.mockResolvedValueOnce({ reading_version_id: `${productId}-retry` });
      fireEvent.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(startMock).toHaveBeenCalledTimes(3);
      expect(startMock.mock.calls[2]?.[1]).toBe(resumeKey);
      expect(loadPendingStartTask(resumeKey)).toBeNull();
    },
  );

  it.each(chartContinuations)(
    "keeps the $productId continuation and key after a late success following timeout",
    async ({ productId, pathname, startMock }) => {
      const resumeKey = await prepareResumedChart(productId, pathname, startMock);
      let releaseStart!: (value: { reading_version_id: string }) => void;
      startMock.mockReturnValueOnce(new Promise((resolve) => {
        releaseStart = resolve;
      }));
      render(createElement(ProductTaskExperience, {
        product: getProductDefinition(productId),
      }));
      const resumedProfileSelect = await screen.findByRole("combobox", {
        name: "排盘资料",
      });
      await waitFor(() => expect(resumedProfileSelect).toHaveValue(profileVersionId));

      vi.useFakeTimers();
      fireEvent.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(startMock).toHaveBeenCalledTimes(2);
      act(() => vi.advanceTimersByTime(60_000));
      const retry = screen.getByRole("button", { name: "重试" });
      expect(retry).toHaveFocus();

      await act(async () => {
        releaseStart({ reading_version_id: `late-${productId}-timeout` });
        await Promise.resolve();
      });
      expect(loadPendingStartTask(resumeKey)).not.toBeNull();

      startMock.mockResolvedValueOnce({ reading_version_id: `${productId}-retry` });
      fireEvent.click(retry);
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(startMock).toHaveBeenCalledTimes(3);
      expect(startMock.mock.calls[2]?.[1]).toBe(resumeKey);
      expect(loadPendingStartTask(resumeKey)).toBeNull();
    },
  );

  it("consumes a successful Bazi continuation so its old URL starts a new reading", async () => {
    mockNavigation.searchParams = new URLSearchParams({ profile: profileVersionId });
    mockListProfiles.mockResolvedValue({ profiles });
    const user = userEvent.setup();
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    expect(profileSelect).toHaveValue(profileVersionId);
    await user.selectOptions(profileSelect, resumedProfileVersionId);
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    expect(await screen.findByRole("link", { name: "登录后继续" })).toBeVisible();

    const resumeKey = mockStartPreviewReading.mock.calls[0]?.[1] as string;
    expect(loadPendingStartTask(resumeKey)).toMatchObject({
      values: { profileVersionId: resumedProfileVersionId },
    });

    cleanup();
    mockNavigation.searchParams = new URLSearchParams({
      profile: profileVersionId,
      idempotency_key: resumeKey,
    });
    mockStartPreviewReading.mockRejectedValueOnce(
      new ApiError("Runtime timeout", 503, undefined, "chart_runtime_timeout"),
    );
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    const resumedSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(resumedSelect).toHaveValue(resumedProfileVersionId));
    const resumedUser = userEvent.setup();
    await resumedUser.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalledTimes(2));
    expect(mockStartPreviewReading.mock.calls[1]?.[0]).toMatchObject({
      profile_version_id: resumedProfileVersionId,
    });
    expect(mockStartPreviewReading.mock.calls[1]?.[1]).toBe(resumeKey);
    expect(loadPendingStartTask(resumeKey)).not.toBeNull();

    mockStartPreviewReading.mockResolvedValueOnce({
      reading_version_id: "reading-after-login",
    });
    await resumedUser.click(await screen.findByRole("button", { name: "重试" }));
    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalledTimes(3));
    expect(mockStartPreviewReading.mock.calls[2]?.[1]).toBe(resumeKey);
    expect(window.sessionStorage.getItem(`mingli.pending-start:${resumeKey}`)).toBeNull();
    expect(loadPendingStartTask(resumeKey)).toBeNull();

    cleanup();
    mockNavigation.searchParams = new URLSearchParams({
      profile: resumedProfileVersionId,
      idempotency_key: resumeKey,
    });
    mockStartPreviewReading.mockResolvedValueOnce({
      reading_version_id: "reading-from-old-url",
    });
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    const oldUrlProfileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(oldUrlProfileSelect).toHaveValue(resumedProfileVersionId));
    await userEvent.setup().click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalledTimes(4));
    expect(mockStartPreviewReading.mock.calls[3]?.[1]).not.toBe(resumeKey);
  });

  it("also consumes a successful non-Bazi continuation", async () => {
    mockNavigation.pathname = "/ziwei";
    const user = userEvent.setup();
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("ziwei"),
    }));

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(profileSelect).toHaveValue(profileVersionId));
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    expect(await screen.findByRole("link", { name: "登录后继续" })).toBeVisible();

    const resumeKey = mockStartZiweiReading.mock.calls[0]?.[1] as string;
    expect(loadPendingStartTask(resumeKey)).not.toBeNull();

    cleanup();
    mockNavigation.searchParams = new URLSearchParams({ idempotency_key: resumeKey });
    mockStartZiweiReading.mockResolvedValueOnce({
      reading_version_id: "ziwei-after-login",
    });
    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("ziwei"),
    }));

    const resumedProfileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(resumedProfileSelect).toHaveValue(profileVersionId));
    await userEvent.setup().click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await waitFor(() => expect(mockStartZiweiReading).toHaveBeenCalledTimes(2));
    expect(window.sessionStorage.getItem(`mingli.pending-start:${resumeKey}`)).toBeNull();
    expect(loadPendingStartTask(resumeKey)).toBeNull();
  });

  it("still honors a valid route profile when there is no continuation", async () => {
    mockNavigation.searchParams = new URLSearchParams({ profile: profileVersionId });
    mockListProfiles.mockResolvedValue({ profiles });

    render(createElement(ProductTaskExperience, {
      product: getProductDefinition("bazi"),
    }));

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    await waitFor(() => expect(profileSelect).toHaveValue(profileVersionId));
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));
    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalledTimes(1));
    expect(mockStartPreviewReading.mock.calls[0]?.[0]).toMatchObject({
      profile_version_id: profileVersionId,
    });
  });
});
