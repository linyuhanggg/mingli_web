import { Clock3, LockKeyhole } from "lucide-react";

import styles from "@/components/app-surface.module.css";
import { RhythmPanel } from "@/components/rhythm-panel";
import { StatusPanel } from "@/components/status-panel";


export default function AppPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>今天，从自己的档案继续。</h1>
        <div>
          <p>今日、近七日、上次解读与待核对项都从已确认资料出发；这里不会先用虚构结果填满首页。</p>
          <div className={styles.metaLine}>
            <span><LockKeyhole aria-hidden="true" size={15} /> 私人页面 · no-store</span>
            <span><Clock3 aria-hidden="true" size={15} /> 状态与正文分开保存</span>
          </div>
        </div>
      </header>

      <div className={styles.dashboard}>
        <RhythmPanel />
        <aside className={styles.rail} aria-labelledby="continue-title">
          <h2 id="continue-title">继续与核对</h2>
          <p>只有真实档案与解读状态会出现在这里。</p>
          <ul className={styles.activityList}>
            <li><strong>继续上次解读</strong><span>登录并完成首份 Accepted 解读后开放</span></li>
            <li><strong>待核对事实</strong><span>当前没有需要核对的真实条目</span></li>
            <li><strong>同盘追问</strong><span>须满足已接纳、范围、次数与期限条件</span></li>
          </ul>
        </aside>
      </div>

      <StatusPanel
        state="disabled"
        title="正式计算与交付仍未接通"
        description="P0 前端界面已经把输入、状态与阅读位置分开；mingli Runtime、模型成稿和真实支付仍是外部门禁，当前不会生成假结果或假成功。"
      />
    </div>
  );
}
