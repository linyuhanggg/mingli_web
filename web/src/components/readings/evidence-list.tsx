import type { ReadingEvidence } from "@/lib/api";

import styles from "./evidence-list.module.css";

export function EvidenceList({
  evidence,
}: Readonly<{ evidence?: ReadingEvidence[] | null }>) {
  const items = Array.isArray(evidence) ? evidence : [];

  return (
    <section className={styles.section} aria-labelledby="evidence-list-heading">
      <h2 id="evidence-list-heading" className={styles.heading}>
        依据来源
      </h2>
      {items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((item) => (
            <li className={styles.item} key={item.ref}>
              <p className={styles.source}>
                {item.source_title}
                {item.locator ? (
                  <span className={styles.locator}> · {item.locator}</span>
                ) : null}
              </p>
              {item.excerpt ? (
                <p className={styles.excerpt}>{item.excerpt}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>服务端暂未返回公开依据来源。</p>
      )}
    </section>
  );
}
