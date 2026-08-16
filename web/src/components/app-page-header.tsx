import type { ReactNode } from "react";

import styles from "./app-surface.module.css";

type AppPageHeaderProps = {
  title: string;
  description: string;
  meta?: ReactNode;
  stacked?: boolean;
};

export function AppPageHeader({
  title,
  description,
  meta,
  stacked = false,
}: AppPageHeaderProps) {
  return (
    <header className={stacked ? `${styles.pageHeader} ${styles.pageHeaderStacked}` : styles.pageHeader}>
      <h1>{title}</h1>
      <div>
        <p>{description}</p>
        {meta ? <div className={styles.metaLine}>{meta}</div> : null}
      </div>
    </header>
  );
}
