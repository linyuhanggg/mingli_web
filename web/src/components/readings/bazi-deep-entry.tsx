import { LockKeyhole } from "lucide-react";
import Link from "next/link";

import styles from "./bazi-deep-entry.module.css";

/** Free-result tail entry. It communicates the lock without rendering deep facts. */
export function BaziDeepEntry() {
  return (
    <aside className={styles.entry} aria-labelledby="bazi-deep-entry-title">
      <LockKeyhole aria-hidden="true" size={22} strokeWidth={1.75} />
      <div>
        <h3 id="bazi-deep-entry-title">专业深读已锁定</h3>
        <p>免费盘面事实保持可见；此处不预填或透露任何深读内容。</p>
      </div>
      <Link href="/pricing">了解专业版</Link>
    </aside>
  );
}
