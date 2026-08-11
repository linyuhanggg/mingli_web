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
import styles from "./private-shell.module.css";


const navigation = [
  { href: "/app", label: "我的首页", mobileLabel: "首页", icon: CalendarDays },
  { href: "/app/profiles", label: "命理档案", mobileLabel: "档案", icon: FolderLock },
  { href: "/app/ask/liuyao", label: "一事一问", mobileLabel: "问事", icon: BookOpenText },
  { href: "/app/readings", label: "解读历史", mobileLabel: "解读", icon: FileClock },
  { href: "/account", label: "个人中心", mobileLabel: "我的", icon: UserRound },
] as const;

function isCurrentDestination(pathname: string, href: string) {
  if (href === "/app") return pathname === href;
  if (href === "/app/profiles") return pathname.startsWith("/app/profile");
  return pathname === href || pathname.startsWith(`${href}/`);
}

function PrivateNavigation({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname() ?? "";

  return (
    <nav
      className={mobile ? styles.mobileNav : styles.sideNav}
      aria-label={mobile ? "移动应用导航" : "私人应用导航"}
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

  return (
    <Link
      aria-label={accessibleName}
      className={styles.identityLink}
      data-state={visualState}
      href="/account"
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

function PrivateShellContent({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname() ?? "/app";
  const mainRef = useRef<HTMLElement>(null);
  const previousPathnameRef = useRef(pathname);

  useEffect(() => {
    if (previousPathnameRef.current === pathname) return;

    previousPathnameRef.current = pathname;
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#private-main">
        跳到主要内容
      </a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <div className={styles.headerActions}>
            <Link className={styles.back} href="/">
              返回公共首页
            </Link>
            <SessionIdentityLink />
          </div>
        </Container>
      </header>
      <Container className={styles.frame}>
        <aside className={styles.aside}>
          <p className={styles.archiveLabel}>私人档案区</p>
          <PrivateNavigation />
          <p className={styles.asideNote}>资料默认不进入公共缓存；正式保存需登录。</p>
        </aside>
        <main
          className={styles.main}
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

export function PrivateShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <AccountSessionBoundary>
      <PrivateShellContent>{children}</PrivateShellContent>
    </AccountSessionBoundary>
  );
}

export { styles as privateShellStyles };
