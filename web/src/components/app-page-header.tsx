import type { ReactNode } from "react";

import styles from "./app-surface.module.css";

type AppPageHeaderProps = {
  title: string;
  description: string;
  meta?: ReactNode;
};

export function AppPageHeader({
  title,
  description,
  meta,
}: AppPageHeaderProps) {
  return (
    <header className={styles.pageHeader}>
      <h1>{title}</h1>
      <div>
        <p>{description}</p>
        {meta ? <div className={styles.metaLine}>{meta}</div> : null}
      </div>
    </header>
  );
}
