import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeEach, describe, expect, it, vi } from "vitest";

import ZeriPage from "@/app/zeri/page";
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

describe("/zeri short route", () => {
  it("connects to /selection without an English 404", async () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/zeri/page.tsx"), "utf8");

    expect(source).toContain('redirect("/selection")');
    expect(source).not.toMatch(/This page could not be found/i);
    expect(source).not.toMatch(/Not Found/);
    expect(source).not.toMatch(/§10|§6\.2|DESIGN/);

    await ZeriPage();

    expect(navigation.redirect).toHaveBeenCalledOnce();
    expect(navigation.redirect).toHaveBeenCalledWith("/selection");

    const redirects = await nextConfig.redirects?.();
    expect(
      redirects?.some((redirect) => redirect.source === "/zeri" && redirect.destination === "/selection"),
    ).toBe(true);
  });
});
