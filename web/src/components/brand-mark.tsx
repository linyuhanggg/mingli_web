import Link from "next/link";

import styles from "./site-chrome.module.css";


export function BrandMark() {
  return (
    <Link className={styles.brand} href="/" aria-label="FateRadar 首页">
      <span className={styles.symbol} aria-hidden="true">
        <span>命</span>
      </span>
      <span>
        <span className={styles.brandTitleRow}>
          <strong>FateRadar</strong>
          <span className={styles.versionPill}>v2.4</span>
        </span>
        <small>命盘 AI · 东方编辑档案</small>
      </span>
    </Link>
  );
}
