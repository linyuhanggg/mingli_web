import type { ReadingFactPanel } from "@/lib/api";
import { formatReadingFacts } from "@/lib/reading-display";

import styles from "./fact-panel.module.css";

export function FactPanel({
  panel,
}: Readonly<{ panel?: ReadingFactPanel | null }>) {
  if (!panel) {
    return <p className={styles.empty}>服务端暂未返回公开事实简报。</p>;
  }

  const facts = formatReadingFacts(panel.facts);
  const primaryFacts = facts.filter((fact) => fact.emphasis === "primary");
  const secondaryFacts = facts.filter((fact) => fact.emphasis === "secondary");

  return (
    <div className={styles.content}>
      <div className={styles.block}>
        <h3 className={styles.heading}>本次问题</h3>
        <p className={styles.question}>{panel.question}</p>
      </div>

      <div className={styles.block}>
        <h3 className={styles.heading}>确定性事实</h3>
        {facts.length > 0 ? (
          <div className={styles.factGroups}>
            {primaryFacts.length > 0 ? (
              <ul className={styles.factCards}>
                {primaryFacts.map((fact) => (
                  <li className={styles.factCard} key={fact.key}>
                    <span className={styles.factLabel}>{fact.label}</span>
                    {fact.pillars ? (
                      <div className={styles.pillars} aria-label={fact.text}>
                        <span>
                          <em>年</em>
                          {fact.pillars.year || "—"}
                        </span>
                        <span>
                          <em>月</em>
                          {fact.pillars.month || "—"}
                        </span>
                        <span>
                          <em>日</em>
                          {fact.pillars.day || "—"}
                        </span>
                        <span>
                          <em>时</em>
                          {fact.pillars.hour || "—"}
                        </span>
                      </div>
                    ) : (
                      <span className={styles.factText}>{fact.text}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : null}

            {secondaryFacts.length > 0 ? (
              <details className={styles.secondaryFacts}>
                <summary>口径与补充事实</summary>
                <ul className={styles.factList}>
                  {secondaryFacts.map((fact) => (
                    <li className={styles.fact} key={fact.key}>
                      <strong>{fact.label}</strong>
                      <span>{fact.text}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : (
          <p className={styles.empty}>本次没有可公开展示的确定性事实。</p>
        )}
      </div>

      {panel.prior_answer ? (
        <div className={styles.block}>
          <h3 className={styles.heading}>上一版已接纳正文</h3>
          <p className={styles.priorAnswer}>{panel.prior_answer}</p>
        </div>
      ) : null}

    </div>
  );
}
