"use client";

import {
  BookOpenText,
  CalendarDays,
  FileClock,
  FolderLock,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";

import {
  AccountSessionBoundary,
  primaryLoginIdentity,
  useAccountSession,
} from "./account-session-context";
import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import { RouteEnter } from "./motion-primitives";
import { SitePrimaryNavigation } from "./site-header";
import styles from "./private-shell.module.css";


const navigation = [
  { href: "/account", label: "我的", mobileLabel: "我的", icon: CalendarDays },
  { href: "/account/profiles", label: "受测人档案", mobileLabel: "档案", icon: FolderLock },
  { href: "/account/history", label: "推演历史", mobileLabel: "历史", icon: FileClock },
  { href: "/account/orders", label: "订单与权益", mobileLabel: "订单", icon: BookOpenText },
  { href: "/account/settings", label: "账户设置", mobileLabel: "设置", icon: UserRound },
] as const;

export type PrivateShellVariant = "account" | "rail";

function isCurrentDestination(pathname: string, href: string) {
  if (href === "/account") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function PrivateNavigation({
  account = false,
  mobile = false,
}: {
  account?: boolean;
  mobile?: boolean;
}) {
  const pathname = usePathname() ?? "";
  const className = mobile
    ? styles.mobileNav
    : account
      ? styles.accountNav
      : styles.sideNav;
  const label = mobile
    ? "移动应用导航"
    : account
      ? "账户中心导航"
      : "私人应用导航";

  return (
    <nav
      className={className}
      aria-label={label}
    >
      {navigation.map(({ href, icon: Icon, label, mobileLabel }) => (
        <Link
          aria-current={isCurrentDestination(pathname, href) ? "page" : undefined}
          href={href}
          key={href}
        >
          <Icon aria-hidden="true" size={19} strokeWidth={1.7} />
          <span>{mobile ? mobileLabel : label}</span>
        </Link>
      ))}
    </nav>
  );
}

function SessionIdentityLink() {
  const { state } = useAccountSession();

  let accessibleName = "正在确认身份，前往个人中心";
  let status = "确认身份";
  let detail = "请稍候";
  let visualState = "checking";
  let Icon = UserRound;

  if (state.status === "signedOut") {
    accessibleName = "当前为游客模式，登录或注册";
    status = "游客模式";
    detail = "登录或注册";
    visualState = "signed-out";
  } else if (state.status === "error") {
    accessibleName = "身份状态未知，前往个人中心";
    status = "身份未知";
    detail = "检查账户";
    visualState = "error";
  } else if (state.status === "signedIn") {
    const identity = primaryLoginIdentity(state.account);
    detail = identity?.masked_destination ?? "已验证账户";
    accessibleName = `已登录，${detail}，前往个人中心`;
    status = "已登录";
    visualState = "signed-in";
    Icon = ShieldCheck;
  }

  const href = state.status === "signedOut" ? "/auth/login" : "/account";

  return (
    <Link
      aria-label={accessibleName}
      className={styles.identityLink}
      data-state={visualState}
      href={href}
    >
      <span className={styles.identityAvatar} aria-hidden="true">
        <Icon size={19} strokeWidth={1.75} />
      </span>
      <span className={styles.identityCopy} aria-hidden="true">
        <small>{status}</small>
        <strong>{detail}</strong>
      </span>
    </Link>
  );
}

function PrivateShellContent({
  children,
  variant,
}: Readonly<{ children: ReactNode; variant: PrivateShellVariant }>) {
  const pathname = usePathname() ?? "/account";
  const mainRef = useRef<HTMLElement>(null);
  const previousPathnameRef = useRef(pathname);
  const accountShell = variant === "account";

  useEffect(() => {
    if (previousPathnameRef.current === pathname) return;

    previousPathnameRef.current = pathname;
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className={accountShell ? `${styles.shell} ${styles.accountShell}` : styles.shell}>
      <a className={styles.skipLink} href="#private-main">
        跳到主要内容
      </a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          {accountShell ? <SitePrimaryNavigation /> : null}
          <div className={styles.headerActions}>
            {!accountShell ? (
              <Link className={styles.back} href="/">
                返回公共首页
              </Link>
            ) : null}
            <SessionIdentityLink />
          </div>
        </Container>
      </header>
      <Container className={styles.frame}>
        {accountShell ? (
          <div className={styles.accountNavigation}>
            <PrivateNavigation account />
          </div>
        ) : (
          <aside className={styles.aside}>
            <p className={styles.archiveLabel}>私人档案区</p>
            <PrivateNavigation />
            <p className={styles.asideNote}>资料默认不进入公共缓存；正式保存需登录。</p>
          </aside>
        )}
        <main
          className={accountShell ? `${styles.main} ${styles.accountMain}` : styles.main}
          id="private-main"
          ref={mainRef}
          tabIndex={-1}
        >
          <RouteEnter routeKey={pathname}>{children}</RouteEnter>
        </main>
      </Container>
      <PrivateNavigation mobile />
    </div>
  );
}

export function PrivateShell({
  children,
  variant = "rail",
}: Readonly<{ children: ReactNode; variant?: PrivateShellVariant }>) {
  return (
    <AccountSessionBoundary>
      <PrivateShellContent variant={variant}>{children}</PrivateShellContent>
    </AccountSessionBoundary>
  );
}

export { styles as privateShellStyles };
