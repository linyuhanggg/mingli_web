import { Clock3, LockKeyhole } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import { ButtonLink } from "@/components/button-link";
import { DashboardHub } from "@/components/dashboard-hub";
import styles from "@/components/app-surface.module.css";


export default function AppPage() {
  return (
    <div className={styles.page}>
      <AppPageHeader
        title="我的命理首页"
        description="从已保存档案、处理中的请求与已交付解读继续；首页只根据当前设备会话和服务端真实记录安排下一步。"
        meta={
          <>
            <span><LockKeyhole aria-hidden="true" size={15} /> 私人页面 · 不使用公共缓存</span>
            <span><Clock3 aria-hidden="true" size={15} /> 状态与正文分开保存</span>
          </>
        }
      />

      <DashboardHub />

      <section className={styles.paper} aria-labelledby="start-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="start-title">全部任务</h2>
            <p>
              需要换一种任务时，从这里直接进入真实流程。
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
              <p>从已确认档案出发，发起确定性八字排盘与覆盖整体格局、状态主线的白话概览。</p>
            </div>
            <ButtonLink href="/app/bazi" variant="text">
              查看八字概览
            </ButtonLink>
          </li>
          <li className={styles.flowItem}>
            <div>
              <h3>一事一问 · 六爻</h3>
              <p>当前支持事业与工作问题；记录卦象、起卦时刻与地点，再生成可核对的解读。</p>
            </div>
            <ButtonLink href="/app/ask/liuyao" variant="text">
              开始六爻起卦
            </ButtonLink>
          </li>
        </ol>
        <div className={styles.actionRow}>
          <ButtonLink href="/app/readings" variant="secondary">
            查看全部解读
          </ButtonLink>
          <ButtonLink href="/account" variant="secondary">
            管理登录与账户
          </ButtonLink>
        </div>
      </section>
    </div>
  );
}
