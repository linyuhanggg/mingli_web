import { AppPageHeader } from "@/components/app-page-header";
import { FortuneFlow } from "@/components/fortune-flow";
import styles from "@/components/app-surface.module.css";


export default function WeekFortunePage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="近七日解读"
        description="从已确认档案启动近七日 fortune 事实面板；范围和参考时间由服务端确认。"
      />
      <FortuneFlow mode="week" />
    </div>
  );
}
