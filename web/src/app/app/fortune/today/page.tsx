import { AppPageHeader } from "@/components/app-page-header";
import { FortuneFlow } from "@/components/fortune-flow";
import styles from "@/components/app-surface.module.css";


export default function TodayFortunePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="今日解读"
        description="选一份已确认的出生档案，查看今天的事业与工作节奏。"
      />
      <FortuneFlow mode="today" />
    </div>
  );
}
