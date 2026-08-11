import type { ReactNode } from "react";

import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";
import styles from "./public-page-shell.module.css";


export function PublicPageShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className={styles.shell}>
      <SiteHeader />
      {children}
      <SiteFooter />
    </div>
  );
}
