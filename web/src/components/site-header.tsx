"use client";

import Link from "next/link";
import { Archive, CalendarRange, MessageCircleQuestion } from "lucide-react";
import { usePathname } from "next/navigation";

import {
  isPublicNavigationItemActive,
  PUBLIC_PRIMARY_NAVIGATION,
  PUBLIC_UTILITY_NAVIGATION,
  type PublicNavigationIcon,
} from "@/lib/product-capabilities";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "./account-session-context";
import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./site-chrome.module.css";


const navigationIcons = {
  archive: Archive,
  calendar: CalendarRange,
  question: MessageCircleQuestion,
} satisfies Record<PublicNavigationIcon, typeof Archive>;

function PublicAccountEntryContent({ pathname }: { pathname: string }) {
  const { state } = useAccountSession();

  const signedIn = state.status === "signedIn";
  const signedOut = state.status === "signedOut";
  const href = signedIn ? "/app" : "/account";
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

export function SiteHeader() {
  const pathname = usePathname() || "/";

  return (
    <>
      <a className={styles.skipLink} href="#main-content">
        跳到主要内容
      </a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <nav className={styles.nav} aria-label="主导航">
            {PUBLIC_PRIMARY_NAVIGATION.map((item) => {
              const Icon = navigationIcons[item.icon];

              return (
                <Link
                  aria-current={
                    isPublicNavigationItemActive(pathname, item) ? "page" : undefined
                  }
                  className={styles.navItem}
                  href={item.href}
                  key={item.href}
                >
                  <Icon aria-hidden="true" size={14} strokeWidth={1.9} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <nav className={styles.headerActions} aria-label="辅助导航">
            {PUBLIC_UTILITY_NAVIGATION.filter((item) => item.href !== "/account").map((item) => (
              <Link
                aria-current={pathname === item.href ? "page" : undefined}
                className={styles.utilityLink}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
            <PublicAccountEntry pathname={pathname} />
          </nav>
        </Container>
      </header>
    </>
  );
}
