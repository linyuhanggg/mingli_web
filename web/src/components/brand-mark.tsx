import Image from "next/image";
import Link from "next/link";

import styles from "./site-chrome.module.css";


export function BrandMark() {
  return (
    <Link className={styles.brand} href="/" aria-label="命理工具首页">
      <Image
        alt=""
        aria-hidden="true"
        className={styles.brandSymbolImage}
        height={48}
        priority
        src="/brand/mingli-mark.webp"
        width={24}
      />
      <span>
        <span className={styles.brandTitleRow}>
          <strong>命理工具</strong>
          <span className={styles.versionPill}>测试版</span>
        </span>
        <small>可核对盘面 · 中性界面</small>
      </span>
    </Link>
  );
}
