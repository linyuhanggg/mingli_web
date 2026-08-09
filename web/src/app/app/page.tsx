import { Clock3, LockKeyhole } from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { privateShellStyles as privateStyles } from "@/components/private-shell";
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

      <section className={privateStyles.panel} aria-label="可用功能">
        <h2>选择一项，开始你的解读。</h2>
        <p>
          先建立可复现的命理档案，再查看今日与近七日提示；也可以不建档，直接就一件具体的事起卦。
        </p>
        <div className={privateStyles.nextGrid}>
          <article className={privateStyles.nextCard}>
            <h2>命理档案</h2>
            <span>确认出生资料与时间口径，保存不可变的档案版本。</span>
            <ButtonLink href="/app/profile/new" variant="text">
              建立命理档案
            </ButtonLink>
          </article>
          <article className={privateStyles.nextCard}>
            <h2>今日与近七日</h2>
            <span>从已确认档案出发，查看服务端确定的日期范围与轻量提示。</span>
            <div className={styles.actionRow}>
              <ButtonLink href="/app/fortune/today" variant="text">
                查看今日
              </ButtonLink>
              <ButtonLink href="/app/fortune/week" variant="text">
                查看近七日
              </ButtonLink>
            </div>
          </article>
          <article className={privateStyles.nextCard}>
            <h2>一事一问 · 六爻</h2>
            <span>记录具体问题、卦象、起卦时刻与地点，再生成可核对的解读。</span>
            <ButtonLink href="/app/ask/liuyao" variant="text">
              开始六爻起卦
            </ButtonLink>
          </article>
        </div>
        <div className={styles.actionRow}>
          <ButtonLink href="/account" variant="secondary">
            管理登录与账户
          </ButtonLink>
        </div>
      </section>

      <StatusPanel
        state="disabled"
        title="正式计算与交付仍未接通"
        description="P0 前端界面已经把输入、状态与阅读位置分开；mingli Runtime、模型成稿和真实支付仍是外部门禁，当前不会生成假结果或假成功。"
      />
    </div>
  );
}
