import { AppPageHeader } from "@/components/app-page-header";
import { FortuneFlow } from "@/components/fortune-flow";
import styles from "@/components/app-surface.module.css";


export default function WeekFortunePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="近七日解读"
        description="选一份已确认的出生档案，查看近七日的事业与工作节奏。"
      />
      <FortuneFlow mode="week" />
    </div>
  );
}
