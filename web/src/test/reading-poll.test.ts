import { describe, expect, it } from "vitest";

import { shouldKeepPolling } from "@/lib/reading-poll";

describe("shouldKeepPolling", () => {
  it("keeps polling delayed when poll_required is true", () => {
    expect(shouldKeepPolling({ status: "delayed", poll_required: true })).toBe(true);
  });

  it("keeps polling delayed when poll_required is omitted, matching the backend stop-status contract", () => {
    expect(shouldKeepPolling({ status: "delayed" })).toBe(true);
  });

  it("stops when poll_required is false even if status is delayed", () => {
    expect(shouldKeepPolling({ status: "delayed", poll_required: false })).toBe(false);
  });

  it("stops accepted and other terminal statuses", () => {
    expect(shouldKeepPolling({ status: "accepted" })).toBe(false);
    expect(shouldKeepPolling({ status: "waiting_input" })).toBe(false);
    expect(shouldKeepPolling({ status: "terminal_stopped" })).toBe(false);
    expect(shouldKeepPolling({ status: "runtime_unknown" })).toBe(false);
    expect(shouldKeepPolling({ status: "accepted", poll_required: true })).toBe(false);
  });

  it("keeps polling in-progress statuses", () => {
    expect(shouldKeepPolling({ status: "queued" })).toBe(true);
    expect(shouldKeepPolling({ status: "preparing" })).toBe(true);
    expect(shouldKeepPolling({ status: "generating" })).toBe(true);
  });
});
