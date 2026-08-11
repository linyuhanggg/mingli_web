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

import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./site-chrome.module.css";


const navigationIcons = {
  archive: Archive,
  calendar: CalendarRange,
  question: MessageCircleQuestion,
} satisfies Record<PublicNavigationIcon, typeof Archive>;

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
            {PUBLIC_UTILITY_NAVIGATION.map((item) => (
              <Link
                aria-current={pathname === item.href ? "page" : undefined}
                className={styles.utilityLink}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </Container>
      </header>
    </>
  );
}
