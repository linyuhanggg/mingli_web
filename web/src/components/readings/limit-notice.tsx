import type { ReadingLimit } from "@/lib/api";

import styles from "./limit-notice.module.css";

export function LimitNotice({
  limits,
}: Readonly<{ limits?: ReadingLimit[] | null }>) {
  const items = Array.isArray(limits) ? limits : [];

  return (
    <section className={styles.section} aria-labelledby="limit-notice-heading">
      <h2 id="limit-notice-heading" className={styles.heading}>
        适用边界
      </h2>
      {items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((limit, index) => (
            <li className={styles.item} key={`${index}-${limit.public_text}`}>
              {limit.public_text}
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>暂无适用边界说明。</p>
      )}
    </section>
  );
}
