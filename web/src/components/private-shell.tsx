import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./private-shell.module.css";


export function PrivateShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <Link className={styles.back} href="/">
            ← 返回公共首页
          </Link>
        </Container>
      </header>
      <main className={styles.main}>
        <Container>{children}</Container>
      </main>
    </div>
  );
}

export { styles as privateShellStyles };
