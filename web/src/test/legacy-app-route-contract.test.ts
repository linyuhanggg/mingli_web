import { beforeEach, describe, expect, it, vi } from "vitest";

import LegacyAppPage from "@/app/app/page";
import LegacyBaziPage from "@/app/app/bazi/page";
import LegacyLiuyaoPage from "@/app/app/ask/liuyao/page";
import LegacyTodayPage from "@/app/app/fortune/today/page";
import LegacyWeekPage from "@/app/app/fortune/week/page";
import LegacyNewProfilePage from "@/app/app/profile/new/page";
import LegacyProfilesPage from "@/app/app/profiles/page";
import LegacyReadingPage from "@/app/app/readings/[readingId]/page";
import LegacyReadingsPage from "@/app/app/readings/page";
import nextConfig from "../../next.config";


const navigation = vi.hoisted(() => ({
  redirect: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
  useParams: () => ({ readingId: "reading-123" }),
  usePathname: () => "/app",
  useRouter: () => ({
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

beforeEach(() => {
  navigation.redirect.mockReset();
});

describe("legacy /app route retirement", () => {
  it.each([
    ["/app", LegacyAppPage, undefined, "/account"],
    ["/app/profiles", LegacyProfilesPage, undefined, "/account/profiles"],
    ["/app/profile/new", LegacyNewProfilePage, undefined, "/account/profiles"],
    ["/app/readings", LegacyReadingsPage, undefined, "/account/history"],
    [
      "/app/readings/[readingId]",
      LegacyReadingPage,
      { params: Promise.resolve({ readingId: "reading-123" }) },
      "/account/history/reading-123",
    ],
    ["/app/bazi", LegacyBaziPage, undefined, "/bazi"],
    ["/app/ask/liuyao", LegacyLiuyaoPage, undefined, "/liuyao"],
  ])("redirects %s to its formal route", async (_route, page, props, destination) => {
    await page(props as never);

    expect(navigation.redirect).toHaveBeenCalledOnce();
    expect(navigation.redirect).toHaveBeenCalledWith(destination);
  });

  it.each([
    ["/app/fortune/today", LegacyTodayPage],
    ["/app/fortune/week", LegacyWeekPage],
  ])("keeps %s as a private fortune entry", async (_route, page) => {
    const rendered = await page();

    expect(rendered).toBeTruthy();
    expect(navigation.redirect).not.toHaveBeenCalled();
  });

  it("does not redirect private fortune entries to the public daily CMS route", async () => {
    const redirects = await nextConfig.redirects?.();

    expect(redirects?.some((redirect) =>
      redirect.source === "/app/fortune/today" || redirect.source === "/app/fortune/week",
    )).toBe(false);
  });
});
