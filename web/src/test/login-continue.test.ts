import { describe, expect, it } from "vitest";

import {
  destinationAfterLogin,
  loadPendingStartTask,
  loginContinueHref,
  persistPendingStartTask,
  safeContinuePath,
} from "@/lib/login-continue";

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
    persistPendingStartTask("intent-1", {
      productId: "liuyao",
      fingerprint: "{\"product\":\"liuyao\"}",
      values: { question: "此问事业", hexagram: "111111" },
    });
    expect(loadPendingStartTask("intent-1")).toEqual({
      productId: "liuyao",
      fingerprint: "{\"product\":\"liuyao\"}",
      values: { question: "此问事业", hexagram: "111111" },
    });
    expect(loadPendingStartTask("missing")).toBeNull();
  });
});
