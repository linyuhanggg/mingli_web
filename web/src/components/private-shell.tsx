"use client";

import {
  BookOpenText,
  CalendarDays,
  FileClock,
  FolderLock,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./private-shell.module.css";


const navigation = [
  { href: "/app", label: "今日", icon: CalendarDays },
  { href: "/app/profiles", label: "档案", icon: FolderLock },
  { href: "/app/ask/liuyao", label: "问事", icon: BookOpenText },
  { href: "/app/readings", label: "解读", icon: FileClock },
  { href: "/account", label: "账户", icon: UserRound },
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
      {navigation.map(({ href, icon: Icon, label }) => (
        <Link
          aria-current={isCurrentDestination(pathname, href) ? "page" : undefined}
          href={href}
          key={href}
        >
          <Icon aria-hidden="true" size={19} strokeWidth={1.7} />
          <span>{label}</span>
        </Link>
      ))}
    </nav>
  );
}

export function PrivateShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#private-main">
        跳到主要内容
      </a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <Link className={styles.back} href="/">
            返回公共首页
          </Link>
        </Container>
      </header>
      <Container className={styles.frame}>
        <aside className={styles.aside}>
          <p className={styles.archiveLabel}>私人档案区</p>
          <PrivateNavigation />
          <p className={styles.asideNote}>资料默认不进入公共缓存；正式保存需登录。</p>
        </aside>
        <main className={styles.main} id="private-main" tabIndex={-1}>
          {children}
        </main>
      </Container>
      <PrivateNavigation mobile />
    </div>
  );
}

export { styles as privateShellStyles };
