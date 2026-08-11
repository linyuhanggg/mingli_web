import type { ReadingEvidence, ReadingFact } from "@/lib/api";
import { formatReadingFact } from "@/lib/reading-display";

import styles from "./evidence-list.module.css";

export function EvidenceList({
  evidence,
  facts = [],
}: Readonly<{
  evidence?: ReadingEvidence[] | null;
  facts?: ReadingFact[];
}>) {
  const items = Array.isArray(evidence) ? evidence : [];
  const publicFactText = new Map(
    facts.map((fact, index) => [fact.ref, formatReadingFact(fact, index).text]),
  );

  return items.length > 0 ? (
    <ul className={styles.list}>
      {items.map((item) => {
        const supportedFacts = Array.from(
          new Set(
            item.supports_fact_refs
              .map((ref) => publicFactText.get(ref))
              .filter((text): text is string => Boolean(text)),
          ),
        );

        return (
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
            {supportedFacts.length > 0 ? (
              <p className={styles.supportedFacts}>
                {`支持事实：${supportedFacts.join("；")}`}
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  ) : (
    <p className={styles.empty}>服务端暂未返回公开依据来源。</p>
  );
}
