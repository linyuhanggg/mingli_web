import type { ReactNode } from "react";

import styles from "./account-section-shell.module.css";

type AccountSectionShellProps = {
  readonly title: string;
  readonly intro: string;
  readonly children: ReactNode;
};

export function AccountSectionShell({ title, intro, children }: AccountSectionShellProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{title}</h1>
        <p>{intro}</p>
      </header>
      {children}
    </div>
  );
}
