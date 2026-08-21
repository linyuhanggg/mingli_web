import Link from "next/link";
import type { ReactNode } from "react";

import { PublicPageShell } from "@/components/public-page-shell";

import styles from "./auth-shell.module.css";

export type AuthShellLink = {
  readonly href: string;
  readonly label: string;
};

type AuthShellProps = {
  readonly title: string;
  readonly intro: string;
  readonly note?: string;
  readonly links: readonly AuthShellLink[];
  readonly children: ReactNode;
};

export function AuthShell({ title, intro, note, links, children }: AuthShellProps) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <div className={styles.column}>
          <header className={styles.header}>
            <h1>{title}</h1>
            <p>{intro}</p>
          </header>
          {children}
          {note ? <p className={styles.note}>{note}</p> : null}
          {links.length ? (
            <nav aria-label="其他认证入口" className={styles.links}>
              <ul>
                {links.map((link) => (
                  <li key={`${link.href}:${link.label}`}>
                    <Link href={link.href}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
        </div>
      </main>
    </PublicPageShell>
  );
}
