import { ZiweiPalaceBoard } from "@/components/readings/ziwei-palace-board";

import { ZIWEI_ENTRY_SILHOUETTE_CAPTION } from "./ziwei-entry-copy";
import styles from "../readings/ziwei-palace-board.module.css";

export function ZiweiEntrySilhouette() {
  return (
    <figure aria-label="紫微空盘剪影" className={styles.silhouetteFigure}>
      <ZiweiPalaceBoard mode="silhouette" />
      <figcaption>{ZIWEI_ENTRY_SILHOUETTE_CAPTION}</figcaption>
    </figure>
  );
}
