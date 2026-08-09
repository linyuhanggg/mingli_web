import type { ReadingFactPanel } from "@/lib/api";
import {
  formatCapabilityIds,
  formatDimensionIds,
  formatHorizon,
  formatObjectId,
} from "@/lib/reading-display";

import styles from "./fact-panel.module.css";

export function FactPanel({
  panel,
}: Readonly<{ panel?: ReadingFactPanel | null }>) {
  if (!panel) {
    return <p className={styles.empty}>服务端暂未返回公开事实简报。</p>;
  }

  return (
    <div className={styles.content}>
      <div className={styles.block}>
        <h3 className={styles.heading}>本次问题</h3>
        <p className={styles.question}>{panel.question}</p>
      </div>

      <div className={styles.block}>
        <h3 className={styles.heading}>确定性事实</h3>
        {panel.facts.length > 0 ? (
          <ul className={styles.factList}>
            {panel.facts.map((fact, index) => (
              <li className={styles.fact} key={`${index}-${fact.display_text}`}>
                {fact.display_text}
              </li>
            ))}
          </ul>
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

      {panel.request_view ? (
        <div className={styles.block}>
          <h3 className={styles.heading}>解读范围</h3>
          <dl className={styles.requestList}>
            <div className={styles.row}>
              <dt className={styles.term}>术法</dt>
              <dd className={styles.desc}>
                {formatCapabilityIds(panel.request_view.capability_ids)}
              </dd>
            </div>
            <div className={styles.row}>
              <dt className={styles.term}>对象</dt>
              <dd className={styles.desc}>
                {formatObjectId(panel.request_view.object_id)}
              </dd>
            </div>
            <div className={styles.row}>
              <dt className={styles.term}>主题</dt>
              <dd className={styles.desc}>
                {formatDimensionIds(panel.request_view.dimension_ids)}
              </dd>
            </div>
            <div className={styles.row}>
              <dt className={styles.term}>服务端目标日期</dt>
              <dd className={styles.desc}>
                {formatHorizon(panel.request_view.horizon)}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}
    </div>
  );
}
