import { AppPageHeader } from "@/components/app-page-header";
import { FortuneFlow } from "@/components/fortune-flow";
import styles from "@/components/app-surface.module.css";


export default function TodayFortunePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="今日解读"
        description="从已确认档案启动今天的 fortune 事实面板；目标日期和时区由服务端确认。"
      />
      <FortuneFlow mode="today" />
    </div>
  );
}
