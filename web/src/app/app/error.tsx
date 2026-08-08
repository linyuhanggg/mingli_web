"use client";

import styles from "@/components/app-surface.module.css";
import { StatusPanel } from "@/components/status-panel";


export default function AppError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className={styles.page}>
      <StatusPanel
        state="error"
        title="私人档案暂时无法载入"
        description="输入没有被当作已经保存，权益也不会因此核销。你可以重试；若问题持续，再从支持页查找对应入口。"
        actionHref="/support"
        actionLabel="查看帮助与支持"
      />
      <button className={styles.secondaryButton} type="button" onClick={reset}>重新载入</button>
    </div>
  );
}
