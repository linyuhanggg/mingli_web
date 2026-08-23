import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeEach, describe, expect, it, vi } from "vitest";

import TimeCheckPage from "@/app/time-check/page";
import nextConfig from "../../next.config";

const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
}));

beforeEach(() => {
  navigation.redirect.mockReset();
});

describe("/time-check short route", () => {
  it("connects to /tools/time-check without an English 404", async () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/time-check/page.tsx"), "utf8");

    expect(source).toContain('redirect("/tools/time-check")');
    expect(source).not.toMatch(/This page could not be found/i);
    expect(source).not.toMatch(/Not Found/);
    expect(source).not.toMatch(/§10|§6\.2|DESIGN/);

    await TimeCheckPage();

    expect(navigation.redirect).toHaveBeenCalledOnce();
    expect(navigation.redirect).toHaveBeenCalledWith("/tools/time-check");

    const redirects = await nextConfig.redirects?.();
    expect(
      redirects?.some(
        (redirect) => redirect.source === "/time-check" && redirect.destination === "/tools/time-check",
      ),
    ).toBe(true);
  });
});
