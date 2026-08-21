"use client";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
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
        description="正在确认账户。"
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
        description="登录后才能查看历史。"
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
      <AccountSectionShell
        intro={detail ? "查看这份任务的版本。" : "查看你的任务和报告。"}
        title={detail ? "历史详情" : "历史"}
      >
        <section
          aria-label={detail ? "历史详情" : "历史"}
          className={styles.accountPanel}
        >
          <AccountHistoryContent readingId={readingId} />
        </section>
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
