import Link from "next/link";

import styles from "./site-chrome.module.css";


export function BrandMark() {
  return (
    <Link className={styles.brand} href="/" aria-label="FateRadar 首页">
      <span className={styles.symbol} aria-hidden="true">
        命
      </span>
      <span>
        <strong>FateRadar</strong>
        <small>命理档案</small>
      </span>
    </Link>
  );
}
