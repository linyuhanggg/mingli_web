import styles from "./time-archive.module.css";


export function TimeArchive() {
  return (
    <figure className={styles.figure} aria-labelledby="time-archive-caption">
      <div className={styles.card}>
        <div className={styles.cardTop}>
          <span>八字</span>
          <span>确定性盘面</span>
        </div>
        <div className={styles.cardCopy}>
          <h3>四柱干支</h3>
          <p>输入精确生辰后，由确定性核心生成可核对盘面。</p>
        </div>
        <dl className={styles.meta}>
          <div>
            <dt>参考典籍</dt>
            <dd>滴天髓 / 子平真诠</dd>
          </div>
          <div>
            <dt>推算核心</dt>
            <dd>确定性 Runtime</dd>
          </div>
        </dl>
      </div>
      <figcaption id="time-archive-caption" className="sr-only">
        八字盘面说明：先确认生辰输入，再由确定性核心排盘。
      </figcaption>
    </figure>
  );
}
