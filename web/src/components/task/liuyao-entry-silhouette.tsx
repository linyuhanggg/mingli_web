import { LIUYAO_ENTRY_SILHOUETTE_CAPTION } from "./liuyao-entry-copy";
import styles from "./task-shell.module.css";

const EMPTY_LINES = [6, 5, 4, 3, 2, 1] as const;
const COLUMN_HEADERS = ["纳甲", "六亲", "六神"] as const;

export function LiuyaoEntrySilhouette() {
  return (
    <figure aria-label="六爻空盘剪影" className={styles.liuyaoSilhouette}>
      <div className={styles.liuyaoTower} aria-hidden="true">
        <div className={styles.liuyaoTowerHead}>
          {COLUMN_HEADERS.map((header) => (
            <span key={header}>{header}</span>
          ))}
        </div>
        <ol>
          {EMPTY_LINES.map((position) => (
            <li key={position} />
          ))}
        </ol>
        <div className={styles.liuyaoShiYing}>
          <span>世</span>
          <span>应</span>
        </div>
      </div>
      <figcaption>{LIUYAO_ENTRY_SILHOUETTE_CAPTION}</figcaption>
    </figure>
  );
}
