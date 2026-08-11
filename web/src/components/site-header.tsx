"use client";

import Link from "next/link";
import { BookOpenText, GitCompareArrows, Home, Sparkles, Users } from "lucide-react";
import { usePathname } from "next/navigation";

import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./site-chrome.module.css";


const navigation = [
  { href: "/", label: "首页", icon: Home },
  { href: "/app/profile/new", label: "在线起盘", icon: Sparkles },
  { href: "/app/bazi", label: "合盘分析", icon: GitCompareArrows },
  { href: "/app/profiles", label: "命理双子", icon: Users },
  { href: "/methodology", label: "学术与古籍库", icon: BookOpenText },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
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
            {navigation.map((item) => (
              <Link
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
                className={styles.navItem}
                href={item.href}
                key={item.href}
              >
                <item.icon aria-hidden="true" size={14} strokeWidth={1.9} />
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>
          <div className={styles.headerActions}>
            <span className={styles.langChip} aria-hidden="true">
              EN
            </span>
            <Link className={styles.proLink} href="/pricing">
              专业版
            </Link>
            <Link className={styles.accountLink} href="/account">
              账户
            </Link>
          </div>
        </Container>
      </header>
    </>
  );
}
