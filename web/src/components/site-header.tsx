"use client";

import {
  CalendarDays,
  ChevronDown,
  Home,
  LayoutGrid,
  UserRound,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Popover as PopoverPrimitive } from "radix-ui";
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "./account-session-context";
import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import { Drawer } from "./ui";
import styles from "./site-chrome.module.css";


// 命盘合参、问事合参只在顶级「合参」菜单出现；放进「术数」会和它重复。
const divinationGroups = [
  {
    label: "命",
    items: [
      { href: "/bazi", label: "八字" },
      { href: "/ziwei", label: "紫微" },
      { href: "/qizheng", label: "七政" },
      { href: "/luming-nayin", label: "禄命纳音" },
    ],
  },
  {
    label: "卦",
    items: [
      { href: "/liuyao", label: "六爻" },
      { href: "/qimen", label: "奇门" },
      { href: "/daliuren", label: "大六壬" },
      { href: "/taiyi", label: "太乙" },
      { href: "/selection", label: "择日" },
    ],
  },
  {
    label: "相",
    items: [
      { href: "/jianxiang", label: "见相" },
      { href: "/fengshui", label: "风水" },
    ],
  },
] as const;

const crossLinks = [
  {
    href: "/hecan",
    label: "命盘合参",
    description: "八字、紫微、七政至少两术互证",
  },
  {
    href: "/wenshi",
    label: "问事合参",
    description: "六爻、大六壬、奇门同题对照",
  },
] as const;

const desktopLinks = [
  { compact: false, href: "/tools", label: "工具" },
  { compact: true, href: "/daily", label: "每日" },
  { compact: true, href: "/library", label: "知识内容" },
] as const;

const mobileLinks = [
  { href: "/", label: "主页", icon: Home },
  { href: "/tools", label: "工具", icon: Wrench },
  { href: "/daily", label: "每日", icon: CalendarDays },
  { href: "/account", label: "我的", icon: UserRound },
] as const;

function isRouteActive(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}

function isDivinationActive(pathname: string) {
  return divinationGroups.some((group) =>
    group.items.some((item) => isRouteActive(pathname, item.href)),
  );
}

function isCrossActive(pathname: string) {
  return crossLinks.some((item) => isRouteActive(pathname, item.href));
}

function PublicAccountEntryContent({ pathname }: { pathname: string }) {
  const { state } = useAccountSession();

  const signedIn = state.status === "signedIn";
  const signedOut = state.status === "signedOut";
  const href = signedOut ? "/auth/login" : "/account";
  const label = signedIn
    ? "已登录 · 我的首页"
    : signedOut
      ? "登录"
      : state.status === "checking"
        ? "确认登录"
        : "身份未知";
  const accessibleName = signedIn
    ? "已登录，进入我的首页"
    : state.status === "checking"
      ? "正在确认登录状态"
      : state.status === "error"
        ? "身份状态暂时未知，前往个人中心"
        : label;

  return (
    <Link
      aria-current={pathname === href ? "page" : undefined}
      aria-label={accessibleName}
      className={styles.utilityLink}
      data-session={signedIn ? "signed-in" : signedOut ? "signed-out" : "unknown"}
      href={href}
    >
      {label}
    </Link>
  );
}

function PublicAccountEntry({ pathname }: { pathname: string }) {
  return (
    <AccountSessionBoundary>
      <PublicAccountEntryContent pathname={pathname} />
    </AccountSessionBoundary>
  );
}

function focusMenuItem(index: number, links: HTMLAnchorElement[]) {
  const nextIndex = (index + links.length) % links.length;
  links[nextIndex]?.focus();
}

function getVisibleMenuItems(menu: HTMLElement) {
  return Array.from(menu.querySelectorAll<HTMLAnchorElement>('[role="menuitem"]')).filter(
    (link) => {
      const computedStyle = window.getComputedStyle(link);
      return !link.hidden && computedStyle.display !== "none" && computedStyle.visibility !== "hidden";
    },
  );
}

function menuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
  const key = event.key;
  if (!(["ArrowDown", "ArrowUp", "Home", "End"] as string[]).includes(key)) return;

  const links = getVisibleMenuItems(event.currentTarget);
  if (links.length === 0) return;

  event.preventDefault();
  const currentIndex = Math.max(0, links.indexOf(document.activeElement as HTMLAnchorElement));
  if (key === "Home") {
    focusMenuItem(0, links);
  } else if (key === "End") {
    focusMenuItem(links.length - 1, links);
  } else if (key === "ArrowDown") {
    focusMenuItem(currentIndex + 1, links);
  } else {
    focusMenuItem(currentIndex - 1, links);
  }
}

function MegaMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname() ?? "/";

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          aria-current={isDivinationActive(pathname) ? "page" : undefined}
          aria-haspopup="menu"
          className={styles.navItem}
          type="button"
          onKeyDown={(event) => {
            if (event.key !== "ArrowDown") return;
            event.preventDefault();
            setOpen(true);
          }}
        >
          <LayoutGrid aria-hidden="true" size={16} strokeWidth={1.8} />
          <span>术数</span>
          <ChevronDown aria-hidden="true" className={styles.chevron} size={15} strokeWidth={1.8} />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          aria-label="术数菜单"
          className={styles.megaMenu}
          role="menu"
          sideOffset={8}
          onKeyDown={menuKeyDown}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            queueMicrotask(() => {
              document.querySelector<HTMLAnchorElement>('[role="menuitem"]')?.focus();
            });
          }}
        >
          {divinationGroups.map((group) => (
            <section className={styles.megaGroup} key={group.label}>
              <h2>{group.label}</h2>
              <div className={styles.megaLinks}>
                {group.items.map((item) => (
                  <Link
                    aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
                    className={styles.megaLink}
                    href={item.href}
                    key={item.href}
                    role="menuitem"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

function CrossMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname() ?? "/";
  const menuRef = useRef<HTMLDivElement>(null);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          aria-current={isCrossActive(pathname) ? "page" : undefined}
          aria-haspopup="menu"
          className={styles.navItem}
          type="button"
          onKeyDown={(event) => {
            if (event.key !== "ArrowDown") return;
            event.preventDefault();
            setOpen(true);
          }}
        >
          <span>合参</span>
          <ChevronDown aria-hidden="true" className={styles.chevron} size={15} strokeWidth={1.8} />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          aria-label="合参菜单"
          className={styles.crossMenu}
          ref={menuRef}
          role="menu"
          sideOffset={8}
          onKeyDown={menuKeyDown}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            queueMicrotask(() => {
              if (menuRef.current) getVisibleMenuItems(menuRef.current)[0]?.focus();
            });
          }}
        >
          {crossLinks.map((item) => (
            <Link
              aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
              className={`${styles.megaLink} ${styles.crossLink}`}
              href={item.href}
              key={item.href}
              role="menuitem"
            >
              <span className={styles.crossLinkBody}>
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </Link>
          ))}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

function MoreMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          aria-haspopup="menu"
          className={styles.navItem}
          type="button"
          onKeyDown={(event) => {
            if (event.key !== "ArrowDown") return;
            event.preventDefault();
            setOpen(true);
          }}
        >
          <span>更多</span>
          <ChevronDown aria-hidden="true" className={styles.chevron} size={15} strokeWidth={1.8} />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="end"
          aria-label="更多菜单"
          className={styles.moreMenu}
          ref={menuRef}
          role="menu"
          sideOffset={8}
          onKeyDown={menuKeyDown}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            queueMicrotask(() => {
              if (menuRef.current) getVisibleMenuItems(menuRef.current)[0]?.focus();
            });
          }}
        >
          {desktopLinks.filter((item) => item.compact).map((item) => (
            <Link
              className={`${styles.megaLink} ${styles.compactMoreLink}`}
              href={item.href}
              key={item.href}
              role="menuitem"
            >
              {item.label}
            </Link>
          ))}
          <Link className={styles.megaLink} href="/about" role="menuitem">
            关于与边界
          </Link>
          <Link className={styles.megaLink} href="/support" role="menuitem">
            帮助与支持
          </Link>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

export function MobileNavigation({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  const historyEntryRef = useRef(false);

  useEffect(() => {
    function handlePopState() {
      if (!historyEntryRef.current) return;
      historyEntryRef.current = false;
      setOpen(false);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!open || historyEntryRef.current) return;
    window.history.pushState(
      { ...(window.history.state ?? {}), siteNavigationDrawer: true },
      "",
      window.location.href,
    );
    historyEntryRef.current = true;
  }, [open]);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && historyEntryRef.current) {
      historyEntryRef.current = false;
      setOpen(false);
      window.history.back();
      return;
    }
    setOpen(nextOpen);
  }

  function handleDrawerLinkClick(event: MouseEvent<HTMLAnchorElement>) {
    if (
      !historyEntryRef.current ||
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }

    historyEntryRef.current = false;
    setOpen(false);
  }

  const drawerTrigger = (
    <button
      aria-expanded={open}
      aria-haspopup="dialog"
      aria-label="打开术数菜单"
      className={styles.mobileNavItem}
      type="button"
    >
      <LayoutGrid aria-hidden="true" size={19} strokeWidth={1.8} />
      <span>术数</span>
    </button>
  );

  return (
    <nav
      aria-label="移动底栏"
      className={styles.mobileBottomBar}
      data-home-chrome={pathname === "/" ? "true" : undefined}
    >
      {mobileLinks.slice(0, 1).map(({ href, label, icon: Icon }) => (
        <Link
          aria-current={isRouteActive(pathname, href) ? "page" : undefined}
          className={styles.mobileNavItem}
          href={href}
          key={href}
        >
          <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
          <span>{label}</span>
        </Link>
      ))}
      <Drawer
        description="按命、卦、相选择入口。"
        open={open}
        side="right"
        title="术数导航"
        trigger={drawerTrigger}
        contentClassName={styles.mobileDrawer}
        onOpenChange={handleOpenChange}
      >
        <div className={styles.mobileDrawerGroups}>
          {divinationGroups.map((group) => (
            <section className={styles.mobileDrawerGroup} key={group.label}>
              <h2>{group.label}</h2>
              <div className={styles.mobileDrawerLinks}>
                {group.items.map((item) => (
                  <Link
                    aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
                    className={styles.mobileDrawerLink}
                    href={item.href}
                    key={item.href}
                    replace
                    onClick={handleDrawerLinkClick}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </Drawer>
      {mobileLinks.slice(1).map(({ href, label, icon: Icon }) => (
        <Link
          aria-current={isRouteActive(pathname, href) ? "page" : undefined}
          className={styles.mobileNavItem}
          href={href}
          key={href}
        >
          <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
          <span>{label}</span>
        </Link>
      ))}
    </nav>
  );
}

export function SitePrimaryNavigation() {
  const pathname = usePathname() || "/";

  return (
    <nav aria-label="主导航" className={`${styles.nav} ${styles.desktopOnly}`}>
      <MegaMenu />
      <CrossMenu />
      {desktopLinks.map((item) => (
        <Link
          aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
          className={`${styles.navItem} ${item.compact ? styles.compactOverflow : ""}`}
          href={item.href}
          key={item.href}
        >
          {item.label}
        </Link>
      ))}
      <MoreMenu />
    </nav>
  );
}

export function SiteHeader({
  includeMobileNavigation = true,
}: Readonly<{ includeMobileNavigation?: boolean }> = {}) {
  const pathname = usePathname() || "/";

  return (
    <>
      <a className={styles.skipLink} href="#main-content">
        跳到主要内容
      </a>
      <header className={styles.header} data-home-chrome={pathname === "/" ? "true" : undefined}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <SitePrimaryNavigation />
          <div className={styles.headerActions}>
            <nav aria-label="账户入口">
              <PublicAccountEntry pathname={pathname} />
            </nav>
          </div>
        </Container>
      </header>
      {includeMobileNavigation ? <MobileNavigation pathname={pathname} /> : null}
    </>
  );
}
