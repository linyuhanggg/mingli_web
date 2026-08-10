import { Clock3, LockKeyhole } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import { ButtonLink } from "@/components/button-link";
import styles from "@/components/app-surface.module.css";
import { RhythmPanel } from "@/components/rhythm-panel";
import { StatusPanel } from "@/components/status-panel";


export default function AppPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="今天，从自己的档案继续。"
        description="今日、近七日、上次解读与待核对项都从已确认资料出发；这里不会先用虚构结果填满首页。"
        meta={
          <>
            <span><LockKeyhole aria-hidden="true" size={15} /> 私人页面 · no-store</span>
            <span><Clock3 aria-hidden="true" size={15} /> 状态与正文分开保存</span>
          </>
        }
      />

      <div className={styles.dashboard}>
        <RhythmPanel />
        <aside className={styles.rail} aria-labelledby="continue-title">
          <h2 id="continue-title">继续与核对</h2>
          <p>只有真实档案与解读状态会出现在这里。</p>
          <ul className={styles.activityList}>
            <li>
              <strong>继续上次解读</strong>
              <span>登录并完成首份已交付解读后开放</span>
            </li>
            <li>
              <strong>待核对事实</strong>
              <span>当前没有需要核对的真实条目</span>
            </li>
            <li>
              <strong>同盘追问</strong>
              <span>须满足已接纳、范围、次数与期限条件</span>
            </li>
          </ul>
        </aside>
      </div>

      <section className={styles.paper} aria-labelledby="start-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="start-title">选择一项，开始你的解读。</h2>
            <p>
              先建立可复现的命理档案，再直接看八字概览或今日/近七日；也可以不建档，直接就一件具体的事起卦。
            </p>
          </div>
        </div>
        <ol className={styles.flowList}>
          <li className={styles.flowItem}>
            <div>
              <h3>命理档案</h3>
              <p>确认出生资料与时间口径，保存不可变的档案版本；建档后可从档案区回看。</p>
            </div>
            <div className={styles.actionRow}>
              <ButtonLink href="/app/profile/new" variant="text">
                建立命理档案
              </ButtonLink>
              <ButtonLink href="/app/profiles" variant="text">
                查看已保存档案
              </ButtonLink>
            </div>
          </li>
          <li className={styles.flowItem}>
            <div>
              <h3>八字概览</h3>
              <p>从已确认档案出发，发起确定性八字排盘与有限概览。</p>
            </div>
            <ButtonLink href="/app/bazi" variant="text">
              查看八字概览
            </ButtonLink>
          </li>
          <li className={styles.flowItem}>
            <div>
              <h3>今日与近七日</h3>
              <p>从已确认档案出发，查看服务端确定的日期范围与轻量提示。</p>
            </div>
            <div className={styles.actionRow}>
              <ButtonLink href="/app/fortune/today" variant="text">
                查看今日
              </ButtonLink>
              <ButtonLink href="/app/fortune/week" variant="text">
                查看近七日
              </ButtonLink>
            </div>
          </li>
          <li className={styles.flowItem}>
            <div>
              <h3>一事一问 · 六爻</h3>
              <p>记录具体问题、卦象、起卦时刻与地点，再生成可核对的解读。</p>
            </div>
            <ButtonLink href="/app/ask/liuyao" variant="text">
              开始六爻起卦
            </ButtonLink>
          </li>
        </ol>
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
