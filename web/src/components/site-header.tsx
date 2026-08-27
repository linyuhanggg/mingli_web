"use client";

import {
  CalendarDays,
  ChevronDown,
  Home,
  LayoutGrid,
  Menu,
  UserRound,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Popover as PopoverPrimitive } from "radix-ui";
import {
  createContext,
  useContext,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "./account-session-context";
import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import { Drawer } from "./ui";
import styles from "./site-chrome.module.css";

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
  { href: "/daily", label: "每日" },
  { href: "/library", label: "知识内容" },
] as const;

const mobileLinks = [
  { href: "/", label: "主页", icon: Home },
  { href: "/tools", label: "工具", icon: Wrench },
  { href: "/daily", label: "每日", icon: CalendarDays },
  { href: "/account", label: "我的", icon: UserRound },
] as const;

const supplementalLinks = [
  { href: "/hecan", label: "命盘合参" },
  { href: "/wenshi", label: "问事合参" },
  { href: "/library", label: "知识内容" },
  { href: "/about", label: "关于与边界" },
  { href: "/support", label: "帮助与支持" },
] as const;

const PublicShellChromeContext = createContext(false);

export function PublicShellChrome({ children }: { children: ReactNode }) {
  return (
    <PublicShellChromeContext.Provider value={true}>
      {children}
    </PublicShellChromeContext.Provider>
  );
}

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
  if (key === "Home") focusMenuItem(0, links);
  else if (key === "End") focusMenuItem(links.length - 1, links);
  else if (key === "ArrowDown") focusMenuItem(currentIndex + 1, links);
  else focusMenuItem(currentIndex - 1, links);
}

function ToolMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname() ?? "/";
  const menuRef = useRef<HTMLDivElement>(null);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          aria-current={isDivinationActive(pathname) || isRouteActive(pathname, "/tools") ? "page" : undefined}
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
          <span>工具</span>
          <ChevronDown aria-hidden="true" className={styles.chevron} size={15} strokeWidth={1.8} />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          aria-label="工具菜单"
          className={styles.megaMenu}
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
          <section className={styles.megaGroup}>
            <h2>总览</h2>
            <div className={styles.megaLinks}>
              <Link className={styles.megaLink} href="/tools" role="menuitem">
                工具总览
              </Link>
              <Link className={styles.megaLink} href="/arts" role="menuitem">
                术数总览
              </Link>
            </div>
          </section>
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

function MobileMenu({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  const trigger = (
    <button
      aria-expanded={open}
      aria-haspopup="dialog"
      aria-label="打开导航菜单"
      className={styles.mobileMenuTrigger}
      type="button"
    >
      <Menu aria-hidden="true" size={21} strokeWidth={1.8} />
      <span>菜单</span>
    </button>
  );

  return (
    <Drawer
      contentClassName={styles.mobileDrawer}
      description="按命、卦、相选择入口，或前往合参与帮助。"
      open={open}
      side="right"
      title="导航菜单"
      trigger={trigger}
      onOpenChange={setOpen}
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
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </section>
        ))}
        <section className={styles.mobileDrawerGroup}>
          <h2>继续</h2>
          <div className={styles.mobileDrawerLinks}>
            {supplementalLinks.map((item) => (
              <Link
                aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
                className={styles.mobileDrawerLink}
                href={item.href}
                key={item.href}
                onClick={() => setOpen(false)}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </Drawer>
  );
}

export function MobileNavigation({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="移动底栏" className={styles.mobileBottomBar}>
      {mobileLinks.map(({ href, label, icon: Icon }) => (
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
      <ToolMenu />
      <CrossMenu />
      {desktopLinks.map((item) => (
        <Link
          aria-current={isRouteActive(pathname, item.href) ? "page" : undefined}
          className={styles.navItem}
          href={item.href}
          key={item.href}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function SiteHeader() {
  const pathname = usePathname() || "/";
  const inPublicShell = useContext(PublicShellChromeContext);

  return (
    <>
      <a className={styles.skipLink} href="#main-content">跳到主要内容</a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <SitePrimaryNavigation />
          <div className={styles.headerActions}>
            <nav aria-label="账户入口" className={styles.desktopAccount}>
              <PublicAccountEntry pathname={pathname} />
            </nav>
            <MobileMenu pathname={pathname} />
          </div>
        </Container>
      </header>
      {inPublicShell ? null : <MobileNavigation pathname={pathname} />}
    </>
  );
}
