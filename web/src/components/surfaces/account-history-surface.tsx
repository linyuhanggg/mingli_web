"use client";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AppPageHeader } from "@/components/app-page-header";
import { ReadingResult } from "@/components/readings/reading-result";
import { ReadingHistory } from "@/components/reading-history";
import { StatusPanel } from "@/components/status-panel";

import { SecondaryStatus } from "./secondary-status";
import styles from "./secondary-surfaces.module.css";

type AccountHistorySurfaceProps = {
  readonly readingId?: string;
};

function AccountHistoryContent({ readingId }: AccountHistorySurfaceProps) {
  const { state } = useAccountSession();

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在确认历史访问权限"
        description="先确认当前账户会话，再读取属于你的 ReadingRoot 和版本摘要。"
      />
    );
  }

  if (state.status === "error") {
    return (
      <StatusPanel
        state="error"
        title="暂时无法确认历史访问权限"
        description={state.message}
      />
    );
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能查看属于你的真实推演历史；当前不会加载任务、盘面或报告。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  return readingId ? <ReadingResult readingId={readingId} /> : <ReadingHistory accountScoped />;
}

export function AccountHistorySurface({ readingId }: AccountHistorySurfaceProps) {
  const detail = Boolean(readingId);

  return (
    <AccountSessionBoundary>
      <div className={styles.accountPage}>
        <AppPageHeader
          description={
            detail
              ? "这份详情只在当前账户拥有对应 ReadingVersion 时展示。"
              : "历史按 ReadingRoot 和 ReadingVersion 组织；列表只展示服务端公开摘要。"
          }
          title={detail ? "一份任务的版本与交付记录" : "任务、版本与报告历史"}
        />
        <section
          aria-label={detail ? "个人中心 · 历史详情" : "个人中心 · 推演历史"}
          className={styles.accountPanel}
        >
          <AccountHistoryContent readingId={readingId} />
        </section>
      </div>
    </AccountSessionBoundary>
  );
}
