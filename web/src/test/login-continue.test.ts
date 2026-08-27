import { describe, expect, it } from "vitest";

import { destinationAfterLogin, safeContinuePath } from "@/lib/login-continue";

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

describe("destinationAfterLogin", () => {
  it("uses the next query when it is a safe relative path", () => {
    window.history.replaceState({}, "", "/auth/login?next=%2Fworkbench");
    expect(destinationAfterLogin()).toBe("/workbench");
  });

  it("falls back when next uses a backslash as an authority separator", () => {
    window.history.replaceState({}, "", "/auth/login?next=%2F%5Cevil.example");
    expect(destinationAfterLogin()).toBe("/account");
  });
});
