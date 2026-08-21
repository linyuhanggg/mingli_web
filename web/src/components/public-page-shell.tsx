"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { SiteFooter } from "./site-footer";
import { MobileNavigation, SiteHeader } from "./site-header";
import styles from "./public-page-shell.module.css";


export function PublicPageShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname() || "/";
  const isHome = pathname === "/";

  return (
    <div className={styles.shell} data-home-chrome={isHome ? "true" : undefined}>
      <SiteHeader />
      {children}
      <MobileNavigation pathname={pathname} />
      <SiteFooter home={isHome} />
    </div>
  );
}
