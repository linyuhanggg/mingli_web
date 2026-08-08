import { Clock3, LockKeyhole } from "lucide-react";

import styles from "@/components/app-surface.module.css";
import { LiuyaoForm } from "@/components/liuyao-form";


export default function LiuyaoPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>一件事，一次起卦，一个明确范围。</h1>
        <div>
          <p>先把问题、时间范围和起卦方式确认清楚。换问题、换卦或重新起卦会形成新的解读根，不会偷算成同盘追问。</p>
          <div className={styles.metaLine}>
            <span><Clock3 aria-hidden="true" size={15} /> 起卦时刻需确认</span>
            <span><LockKeyhole aria-hidden="true" size={15} /> 问题正文不进入 URL</span>
          </div>
        </div>
      </header>
      <LiuyaoForm />
    </div>
  );
}
