import { HexagramFigure } from "@/components/readings/hexagram-glyphs";

import { MEIHUA_ENTRY_SILHOUETTE_CAPTION } from "./meihua-entry-copy";
import styles from "./task-shell.module.css";

const HEXAGRAM_SLOTS = ["本", "互", "变"] as const;
const EMPTY_LINES = [
  { yang: true, moving: false },
  { yang: true, moving: false },
  { yang: true, moving: false },
  { yang: true, moving: false },
  { yang: true, moving: false },
  { yang: true, moving: false },
] as const;

export function MeihuaEntrySilhouette() {
  return (
    <figure aria-label="梅花空盘剪影" className={styles.meihuaSilhouette}>
      <div className={styles.meihuaTriad} aria-hidden="true">
        {HEXAGRAM_SLOTS.map((slot) => (
          <div className={styles.meihuaHexagramSlot} key={slot}>
            <strong>{slot}</strong>
            <HexagramFigure lines={EMPTY_LINES} silhouette size="s" />
          </div>
        ))}
      </div>
      <div className={styles.meihuaBodyUse} aria-hidden="true">
        <span>体</span>
        <span>用</span>
      </div>
      <figcaption>{MEIHUA_ENTRY_SILHOUETTE_CAPTION}</figcaption>
    </figure>
  );
}
