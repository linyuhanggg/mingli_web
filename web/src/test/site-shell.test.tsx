import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentPropsWithoutRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SiteHeader } from "@/components/site-header";


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
  usePathname: () => "/",
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));


beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
});


describe("public shell navigation", () => {
  it("exposes the frozen desktop entry set and grouped divination menu", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(within(navigation).getByRole("button", { name: "术数" })).toBeVisible();
    expect(within(navigation).getByRole("button", { name: "合参" })).toBeVisible();
    expect(within(navigation).getByRole("link", { name: "工具" })).toHaveAttribute(
      "href",
      "/tools",
    );
    expect(within(navigation).getByRole("link", { name: "每日" })).toHaveAttribute(
      "href",
      "/daily",
    );
    expect(within(navigation).getByRole("link", { name: "知识内容" })).toHaveAttribute(
      "href",
      "/library",
    );
    expect(
      screen.getAllByRole("link").find((link) => link.getAttribute("href") === "/account"),
    ).toBeDefined();

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
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("menu", { name: "合参菜单" })).not.toBeInTheDocument());

    await user.click(within(navigation).getByRole("button", { name: "术数" }));
    const menu = screen.getByRole("menu", { name: "术数菜单" });
    for (const label of [
      "命",
      "八字",
      "紫微",
      "七政",
      "禄命纳音",
      "命盘合参",
      "卦",
      "六爻",
      "奇门",
      "大六壬",
      "太乙",
      "择日",
      "问事合参",
      "相",
      "见相",
      "风水",
    ]) {
      expect(within(menu).getByText(label, { exact: true })).toBeVisible();
    }
    expect(within(menu).queryByText("多盘问答")).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click(within(navigation).getByRole("button", { name: "更多" }));
    const moreMenu = screen.getByRole("menu", { name: "更多菜单" });
    expect(within(moreMenu).getByRole("menuitem", { name: "每日" })).toHaveAttribute(
      "href",
      "/daily",
    );
    expect(within(moreMenu).getByRole("menuitem", { name: "知识内容" })).toHaveAttribute(
      "href",
      "/library",
    );
  });

  it("closes the desktop menu with Escape and returns focus to its trigger", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "术数" });
    await user.click(trigger);
    expect(screen.getByRole("menu", { name: "术数菜单" })).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu", { name: "术数菜单" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("supports ArrowDown and roving arrow navigation inside the desktop menu", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "术数" });
    trigger.focus();
    await user.keyboard("{ArrowDown}");

    const menu = screen.getByRole("menu", { name: "术数菜单" });
    const bazi = within(menu).getByRole("menuitem", { name: "八字" });
    const ziwei = within(menu).getByRole("menuitem", { name: "紫微" });
    await waitFor(() => expect(bazi).toHaveFocus());

    await user.keyboard("{ArrowDown}");
    expect(ziwei).toHaveFocus();
    await user.keyboard("{Home}");
    expect(bazi).toHaveFocus();
  });

  it("supports complete keyboard navigation inside the More menu", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "更多" });
    trigger.focus();
    await user.keyboard("{ArrowDown}");

    const menu = screen.getByRole("menu", { name: "更多菜单" });
    const items = within(menu).getAllByRole("menuitem");
    await waitFor(() => expect(items[0]).toHaveFocus());

    await user.keyboard("{ArrowDown}");
    expect(items[1]).toHaveFocus();
    await user.keyboard("{ArrowUp}");
    expect(items[0]).toHaveFocus();
    await user.keyboard("{End}");
    expect(items.at(-1)).toHaveFocus();
    await user.keyboard("{Home}");
    expect(items[0]).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu", { name: "更多菜单" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("skips hidden More items during arrow navigation", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    await user.click(screen.getByRole("button", { name: "更多" }));
    const menu = screen.getByRole("menu", { name: "更多菜单" });
    const items = within(menu).getAllByRole("menuitem");
    items[1].hidden = true;
    items[0].focus();

    await user.keyboard("{ArrowDown}");
    expect(items[2]).toHaveFocus();
  });

  it("provides the five-item mobile bottom bar and a full-screen divination drawer", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    expect(within(bottomBar).getAllByRole("link", { hidden: true })).toHaveLength(4);
    expect(within(bottomBar).getByRole("link", { name: "主页", hidden: true })).toHaveAttribute("href", "/");
    expect(within(bottomBar).getByRole("link", { name: "工具", hidden: true })).toHaveAttribute(
      "href",
      "/tools",
    );
    expect(within(bottomBar).getByRole("link", { name: "每日", hidden: true })).toHaveAttribute(
      "href",
      "/daily",
    );
    expect(within(bottomBar).getByRole("link", { name: "我的", hidden: true })).toHaveAttribute(
      "href",
      "/account",
    );

    const trigger = within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "术数导航" })).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "术数导航" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("closes the mobile drawer when browser back is dispatched", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    const trigger = within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "术数导航" })).toBeVisible();

    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "术数导航" })).not.toBeInTheDocument();
      expect(trigger).toHaveFocus();
    });
  });

  it("uses the drawer history entry for link navigation and closes the drawer", async () => {
    const user = userEvent.setup();
    render(<SiteHeader />);

    const bottomBar = screen.getByLabelText("移动底栏");
    await user.click(
      within(bottomBar).getByRole("button", { name: "打开术数菜单", hidden: true }),
    );

    const drawer = screen.getByRole("dialog", { name: "术数导航" });
    expect(window.history.state).toMatchObject({ siteNavigationDrawer: true });
    await user.click(within(drawer).getByRole("link", { name: "八字" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "术数导航" })).not.toBeInTheDocument();
      expect(window.location.pathname).toBe("/bazi");
    });
    window.history.back();
    await waitFor(() => expect(window.location.pathname).toBe("/"));
  });
});

describe("public shell responsive and cache contracts", () => {
  it("keeps the 767/768 boundary and reserves mobile safe-area space", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/site-chrome.module.css"),
      "utf8",
    );

    expect(css).toMatch(/@media \(max-width:\s*47\.999rem\)/);
    expect(css).toMatch(/@media \(min-width:\s*48rem\)/);
    expect(css).toMatch(/\.header[\s\S]*min-height:\s*var\(--header-mobile\)/);
    expect(css).toMatch(/\.desktopOnly[\s\S]*display:\s*none/);
    expect(css).toMatch(/\.mobileBottomBar[\s\S]*min-height:\s*var\(--nav-bottom\)/);
    expect(css).toMatch(/env\(safe-area-inset-bottom\)/);
    expect(css).toMatch(/overflow-x:\s*hidden/);
    expect(css).toMatch(/\.mobileDrawer[\s\S]*width:\s*100vw/);
    expect(css).toMatch(
      /@media \(min-width:\s*48rem\) and \(max-width:\s*63\.999rem\)[\s\S]*\.compactOverflow[\s\S]*display:\s*none/,
    );
    expect(css).toMatch(
      /@media \(min-width:\s*48rem\) and \(max-width:\s*63\.999rem\)[\s\S]*\.compactMoreLink[\s\S]*display:\s*flex/,
    );
    expect(css).not.toMatch(/letter-spacing/);
  });

  it("backs every shell destination with either a product surface or a public page", () => {
    for (const route of [
      "/about",
      "/daily",
      "/library",
      "/tools",
    ]) {
      const source = readFileSync(resolve(process.cwd(), `src/app${route}/page.tsx`), "utf8");
      expect(source).toMatch(/EditorialPage|PublicPageShell|SecondarySurface|PublicContentSurface/);
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

    // /canwen 于 2026-08-14 并入命盘合参：路由保留，但只作为重定向兜底（next.config 已做请求层重定向）。
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
