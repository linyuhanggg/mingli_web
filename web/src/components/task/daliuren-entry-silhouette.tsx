import { DaliurenBoard } from "@/components/readings/daliuren-board";

import { DALIUREN_ENTRY_SILHOUETTE_CAPTION } from "./daliuren-entry-copy";
import styles from "../readings/daliuren-board.module.css";

export function DaliurenEntrySilhouette() {
  return (
    <figure aria-label="大六壬空盘剪影" className={styles.entrySilhouette}>
      <DaliurenBoard mode="silhouette" />
      <figcaption>{DALIUREN_ENTRY_SILHOUETTE_CAPTION}</figcaption>
    </figure>
  );
}
