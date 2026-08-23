"use client";

import styles from "./ziwei-caliber-bar.module.css";

export type ZiweiCaliberBarProps = {
  chineseDate?: string | null;
};

function readDate(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

export function ZiweiCaliberBar({ chineseDate = null }: ZiweiCaliberBarProps) {
  const date = readDate(chineseDate);
  if (!date) return null;

  return (
    <section aria-label="口径" className={styles.bar} data-slot="caliber">
      <p className={styles.date}>{date}</p>
    </section>
  );
}
