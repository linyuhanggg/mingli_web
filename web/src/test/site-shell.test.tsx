import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentPropsWithoutRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublicPageShell } from "@/components/public-page-shell";
import { SiteHeader } from "@/components/site-header";
import { ApiError } from "@/lib/api";

const { getAccountMock, usePathnameMock } = vi.hoisted(() => ({
  getAccountMock: vi.fn(),
  usePathnameMock: vi.fn(),
}));

type TestLinkProps = ComponentPropsWithoutRef<"a"> & {
  href: string;
  replace?: boolean;
};

vi.mock("next/link", () => ({
  default: ({ href, onClick, replace, ...props }: TestLinkProps) => (
    <a
      {...props}
      data-history-mode={replace ? "replace" : "push"}
      href={href}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented) return;
        window.history[replace ? "replaceState" : "pushState"](null, "", href);
      }}
    />
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: getAccountMock,
}));

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  getAccountMock.mockReset();
  getAccountMock.mockImplementation(() => new Promise(() => undefined));
  usePathnameMock.mockReset();
  usePathnameMock.mockReturnValue("/");
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("public shell navigation", () => {
  it("exposes the frozen desktop entry set and grouped tool menu", async () => {
    const user = userEvent.setup();
    getAccountMock.mockRejectedValueOnce(new ApiError("未登录", 401));
    render(<SiteHeader />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(within(navigation).getByRole("button", { name: "工具" })).toBeVisible();
    expect(within(navigation).getByRole("button", { name: "合参" })).toBeVisible();
    expect(within(navigation).getByRole("link", { name: "人生 K 线" })).toHaveAttribute(
      "href",
      "/life-kline",
    );
    expect(within(navigation).queryByRole("link", { name: "每日" })).not.toBeInTheDocument();
    expect(within(navigation).queryByRole("link", { name: "知识内容" })).not.toBeInTheDocument();
    expect(within(navigation).queryByRole("link", { name: "工具" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "正在确认登录状态" })).toHaveAttribute(
      "href",
      "/account",
    );
    expect(await screen.findByRole("link", { name: "登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );

    await user.click(within(navigation).getByRole("button", { name: "工具" }));
    const menu = screen.getByRole("menu", { name: "工具菜单" });
    expect(within(menu).getByRole("menuitem", { name: "工具总览" })).toHaveAttribute(
      "href",
      "/tools",
    );
    expect(within(menu).getByRole("menuitem", { name: "术数总览" })).toHaveAttribute(
      "href",
      "/arts",
    );
    for (const label of [
      "命",
      "八字",
      "紫微",
      "七政",
      "禄命纳音",
      "卦",
      "六爻",
      "奇门",
      "大六壬",
      "太乙",
      "择日",
      "相",
      "见相",
      "风水",
    ]) {
      expect(within(menu).getByText(label, { exact: true })).toBeVisible();
    }
    expect(within(menu).queryByText("命盘合参", { exact: true })).not.toBeInTheDocument();
    expect(within(menu).queryByText("问事合参", { exact: true })).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click(within(navigation).getByRole("button", { name: "合参" }));
    const crossMenu = screen.getByRole("menu", { name: "合参菜单" });
    expect(within(crossMenu).getByRole("menuitem", { name: /命盘合参/ })).toHaveAttribute(
      "href",
      "/hecan",
    );
    expect(within(crossMenu).getByRole("menuitem", { name: /问事合参/ })).toHaveAttribute(
      "href",
      "/wenshi",
    );
  });

  it("marks the arts overview as the current tool section", () => {
    usePathnameMock.mockReturnValue("/arts");
    render(<SiteHeader />);

    expect(screen.getByRole("button", { name: "工具" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      within(screen.getByLabelText("移动底栏")).getByRole("link", {
        name: "工具",
        hidden: true,
      }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("keeps divination routes on an independent mobile navigation item", () => {
    usePathnameMock.mockReturnValue("/bazi/hepan");
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    expect(
      within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      within(bottomBar).getByRole("link", { name: "工具", hidden: true }),
    ).not.toHaveAttribute("aria-current");
  });

  it("closes the desktop menu with Escape and returns focus to its trigger", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "工具" });
    await user.click(trigger);
    expect(screen.getByRole("menu", { name: "工具菜单" })).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu", { name: "工具菜单" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("supports ArrowDown and roving arrow navigation inside the tool menu", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "工具" });
    trigger.focus();
    await user.keyboard("{ArrowDown}");

    const menu = screen.getByRole("menu", { name: "工具菜单" });
    const overview = within(menu).getByRole("menuitem", { name: "工具总览" });
    const arts = within(menu).getByRole("menuitem", { name: "术数总览" });
    await waitFor(() => expect(overview).toHaveFocus());

    await user.keyboard("{ArrowDown}");
    expect(arts).toHaveFocus();
    await user.keyboard("{End}");
    expect(within(menu).getByRole("menuitem", { name: "风水" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(overview).toHaveFocus();
  });

  it("skips hidden entries during desktop menu arrow navigation", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    await user.click(screen.getByRole("button", { name: "工具" }));
    const menu = screen.getByRole("menu", { name: "工具菜单" });
    const items = within(menu).getAllByRole("menuitem");
    items[1].hidden = true;
    items[0].focus();

    await user.keyboard("{ArrowDown}");
    expect(items[2]).toHaveFocus();
  });

  it("provides the governed five-item mobile bottom bar and full-screen divination drawer", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    expect(within(bottomBar).getAllByRole("link", { hidden: true })).toHaveLength(4);
    for (const [name, href] of [
      ["主页", "/"],
      ["工具", "/tools"],
      ["人生 K 线", "/life-kline"],
      ["我的", "/account"],
    ] as const) {
      expect(within(bottomBar).getByRole("link", { name, hidden: true })).toHaveAttribute(
        "href",
        href,
      );
    }
    const trigger = within(bottomBar).getByRole("button", {
      name: "打开术数菜单",
      hidden: true,
    });
    expect(trigger).toHaveTextContent("术数");
    expect(
      within(bottomBar).getByRole("link", { name: "人生 K 线", hidden: true }).querySelector("svg"),
    ).toBeNull();

    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "术数导航" })).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "术数导航" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("closes the mobile drawer on link activation without synthetic history state", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    await user.click(
      within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true }),
    );
    const drawer = screen.getByRole("dialog", { name: "术数导航" });
    await user.click(within(drawer).getByRole("link", { name: "八字" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "术数导航" })).not.toBeInTheDocument();
      expect(window.location.pathname).toBe("/bazi");
    });

    const source = readFileSync(resolve(process.cwd(), "src/components/site-header.tsx"), "utf8");
    expect(source).not.toMatch(/pushState|replaceState|popstate|siteNavigationDrawer/);
  });
});

describe("public shell responsive and cache contracts", () => {
  it("keeps the brand mark legible in explicit and opted-in system dark themes", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/site-chrome.module.css"),
      "utf8",
    );
    const layout = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");

    expect(layout).toContain('data-theme-system="auto"');
    expect(css).toMatch(
      /\.brandSymbolImage\s*\{[^}]*filter:\s*grayscale\(1\) contrast\(1\.08\)/,
    );
    expect(css).toMatch(
      /:global\(\[data-theme="dark"\]\)\s+\.brandSymbolImage\s*\{[^}]*filter:[^;}]*invert\(1\)/,
    );
    expect(css).toMatch(
      /@media \(prefers-color-scheme:\s*dark\)[\s\S]*:global\(:root\[data-theme-system="auto"\]:not\(\[data-theme\]\)\)\s+\.brandSymbolImage\s*\{[^}]*filter:[^;}]*invert\(1\)/,
    );
  });

  it("keeps desktop header controls at 44px for every pointer type", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/site-chrome.module.css"),
      "utf8",
    );

    expect(css).toMatch(
      /\.navItem\s*\{[^}]*min-width:\s*var\(--ds-touch-min\)[^}]*min-height:\s*var\(--ds-touch-min\)/,
    );
    expect(css).toMatch(
      /\.utilityLink\s*\{[^}]*min-width:\s*var\(--ds-touch-min\)[^}]*min-height:\s*var\(--ds-touch-min\)/,
    );
    expect(css).toMatch(
      /@media \(min-width:\s*840px\) and \(any-pointer:\s*coarse\)\s*\{[\s\S]*?\.navItem,\s*\.utilityLink\s*\{[^}]*min-width:\s*var\(--ds-touch-min\)[^}]*min-height:\s*var\(--ds-touch-min\)/,
    );
  });

  it.each([360, 768])(
    "keeps the mobile bottom bar in static flow with its own safe area at %ipx",
    (viewportWidth) => {
      const css = readFileSync(
        resolve(process.cwd(), "src/components/site-chrome.module.css"),
        "utf8",
      );
      const shellCss = readFileSync(
        resolve(process.cwd(), "src/components/public-page-shell.module.css"),
        "utf8",
      );

      expect(viewportWidth).toBeLessThan(840);
      expect(css).toMatch(/@media \(max-width:\s*839px\)/);
      expect(css).toMatch(/\.header[\s\S]*min-height:\s*var\(--header-desktop\)/);
      expect(css).toMatch(/@media \(max-width:\s*839px\)[\s\S]*\.header,[\s\S]*min-height:\s*var\(--header-mobile\)/);
      expect(css).toMatch(/\.mobileBottomBar\s*\{[^}]*position:\s*static/);
      expect(css).not.toMatch(/\.mobileBottomBar\s*\{[^}]*position:\s*(?:fixed|sticky)/);
      expect(css).not.toMatch(/\.mobileBottomBar\s*\{[^}]*bottom:\s*0/);
      expect(css).toMatch(/\.mobileBottomBar[\s\S]*grid-template-columns:\s*repeat\(5,/);
      expect(css).toMatch(/\.mobileBottomBar\s*\{[^}]*min-height:\s*calc\(var\(--nav-bottom\) \+ env\(safe-area-inset-bottom\)\)/);
      expect(css).toMatch(/env\(safe-area-inset-bottom\)/);
      expect(css).toMatch(/overflow-x:\s*clip/);
      expect(css).toMatch(/\.mobileDrawer\.mobileDrawer\s*\{[^}]*width:\s*100vw/);
      expect(shellCss).not.toMatch(/padding-bottom:\s*calc\(var\(--nav-bottom\)/);
      expect(shellCss).not.toMatch(/scroll-padding-bottom:\s*calc\(var\(--nav-bottom\)/);
    },
  );

  it("keeps the static mobile navigation mutually exclusive with desktop navigation at 840px", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/site-chrome.module.css"),
      "utf8",
    );

    expect(css).toMatch(/@media \(min-width:\s*840px\)/);
    expect(css).toMatch(/@media \(min-width:\s*840px\)[\s\S]*\.mobileBottomBar,[\s\S]*display:\s*none/);
    expect(css).toMatch(/\.desktopOnly\s*\{[^}]*display:\s*flex/);
    expect(css).toMatch(/@media \(max-width:\s*839px\)[\s\S]*\.desktopOnly,[\s\S]*display:\s*none/);
  });

  it("places the five-item mobile navigation after main content without a padding workaround", () => {
    usePathnameMock.mockReturnValue("/bazi");
    render(
      <PublicPageShell>
        <main id="main-content">八字录入</main>
      </PublicPageShell>,
    );

    const main = screen.getByRole("main");
    const bottomBar = screen.getByLabelText("移动底栏");
    expect(main.compareDocumentPosition(bottomBar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(bottomBar).getAllByRole("link", { hidden: true })).toHaveLength(4);
    expect(
      within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true }),
    ).toBeInTheDocument();
  });

  it("renders only explicitly supplied breadcrumb states and fails closed otherwise", () => {
    usePathnameMock.mockReturnValue("/workbench/private-handle");
    const inferredReadyView = render(
      <PublicPageShell>
        <main id="main-content">结果</main>
      </PublicPageShell>,
    );

    const inferredReadyBreadcrumb = screen.getByRole("navigation", { name: "面包屑" });
    expect(inferredReadyBreadcrumb.querySelector("[data-state]")).toBeNull();
    expect(inferredReadyBreadcrumb).not.toHaveTextContent("private-handle");
    inferredReadyView.unmount();

    const explicitReadyView = render(
      <PublicPageShell breadcrumbStatus="ready">
        <main id="main-content">结果</main>
      </PublicPageShell>,
    );
    expect(screen.getByLabelText("当前状态：READY")).toHaveAttribute(
      "data-state",
      "ready",
    );
    explicitReadyView.unmount();

    usePathnameMock.mockReturnValue("/bazi/hepan");
    const inferredInputView = render(
      <PublicPageShell>
        <main id="main-content">合盘录入</main>
      </PublicPageShell>,
    );
    expect(screen.getByRole("navigation", { name: "面包屑" }).querySelector("[data-state]"))
      .toBeNull();
    inferredInputView.unmount();

    const explicitInputView = render(
      <PublicPageShell breadcrumbStatus="need-input">
        <main id="main-content">合盘录入</main>
      </PublicPageShell>,
    );
    expect(screen.getByLabelText("当前状态：NEED-INPUT")).toHaveAttribute(
      "data-state",
      "need-input",
    );
    explicitInputView.unmount();

    render(
      <PublicPageShell breadcrumbStatus="future-state">
        <main id="main-content">未知状态</main>
      </PublicPageShell>,
    );
    expect(screen.queryByText("FUTURE-STATE")).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "面包屑" }).querySelector("[data-state]")).toBeNull();
  });

  it("uses the shared loading Status for every relationship Suspense fallback", () => {
    for (const product of ["bazi", "ziwei", "qizheng"] as const) {
      const source = readFileSync(
        resolve(process.cwd(), `src/app/${product}/hepan/page.tsx`),
        "utf8",
      );
      expect(source).toMatch(/<Status[\s\S]*state="loading"/);
      expect(source).not.toContain("<p>正在加载合盘…</p>");
    }
  });

  it("backs every shell destination with either a product surface or a public page", () => {
    const publicPageWrappers = {
      "/about": ["EditorialPage"],
      "/daily": ["RetiredPublicSurface"],
      "/library": ["RetiredPublicSurface"],
      "/life-kline": ["LifeKlinePage"],
      "/tools": ["ToolsPageFrame", "ToolsIndexView"],
    } as const;

    for (const [route, wrappers] of Object.entries(publicPageWrappers)) {
      const source = readFileSync(resolve(process.cwd(), `src/app${route}/page.tsx`), "utf8");
      for (const wrapper of wrappers) {
        expect(source, `${route} must render ${wrapper}`).toContain(wrapper);
      }
    }

    for (const route of [
      "/bazi",
      "/daliuren",
      "/hecan",
      "/jianxiang",
      "/liuyao",
      "/qimen",
      "/qizheng",
      "/wenshi",
      "/ziwei",
    ]) {
      const source = readFileSync(resolve(process.cwd(), `src/app${route}/page.tsx`), "utf8");
      expect(source).toContain("ProductTaskPage");
      expect(source).not.toContain("EditorialPage");
      expect(source).not.toContain("页面已预制");
    }

    const canwenSource = readFileSync(resolve(process.cwd(), "src/app/canwen/page.tsx"), "utf8");
    expect(canwenSource).toContain('redirect("/hecan")');
    expect(canwenSource).not.toContain("ProductTaskPage");
  });

  it("keeps the retired product name out of visible public pages", () => {
    for (const file of [
      "src/app/page.tsx",
      "src/app/methodology/page.tsx",
      "src/app/pricing/page.tsx",
      "src/app/privacy/page.tsx",
      "src/app/support/page.tsx",
      "src/app/terms/page.tsx",
    ]) {
      expect(readFileSync(resolve(process.cwd(), file), "utf8")).not.toContain("FateRadar");
    }
  });

  it("keeps private paths out of the service worker cache", () => {
    const serviceWorker = readFileSync(resolve(process.cwd(), "public/sw.js"), "utf8");

    expect(serviceWorker).toContain("/app/");
    expect(serviceWorker).toContain("/account");
    expect(serviceWorker).toContain("/auth/");
    expect(serviceWorker).toContain("/workbench/");
    expect(serviceWorker).toContain("/checkout/");
    expect(serviceWorker).toContain("/share/");
    expect(serviceWorker).toContain("/invite/");
    expect(serviceWorker).toContain('const PUBLIC_CACHE = "mingli-public-v2"');
    expect(serviceWorker).toContain("no-store");
    expect(serviceWorker).toContain("isPublicDocumentNavigation");
    expect(serviceWorker).toContain("cache.put(event.request, response.clone())");
    expect(serviceWorker).toContain(".filter((cacheName) => cacheName.startsWith(\"mingli-public-\")");
    expect(serviceWorker).toMatch(/if \(isPrivatePath\(url\.pathname\)\)[\s\S]*fetch\(event\.request/);
    expect(serviceWorker).toMatch(/url\.pathname\.startsWith\("\/api\/"\)/);
    expect(serviceWorker).toMatch(/isCacheablePublicRequest/);
  });

  it("registers the service worker only through the root public shell", () => {
    const rootLayout = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");

    expect(rootLayout).toContain("ServiceWorkerRegistration");
    const registration = readFileSync(resolve(process.cwd(), "src/components/service-worker-registration.tsx"), "utf8");
    expect(registration).toContain('register("/sw.js"');
    expect(registration).toContain('updateViaCache: "none"');
  });
});
