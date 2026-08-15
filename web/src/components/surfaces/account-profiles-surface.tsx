"use client";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AppPageHeader } from "@/components/app-page-header";
import { ProfileArchive } from "@/components/profile-archive";
import { StatusPanel } from "@/components/status-panel";

import { SecondaryStatus } from "./secondary-status";
import styles from "./secondary-surfaces.module.css";

function AccountProfilesContent() {
  const { state } = useAccountSession();

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在确认档案访问权限"
        description="先确认当前账户会话，再读取属于你的 ProfileVersion 摘要。"
      />
    );
  }

  if (state.status === "error") {
    return (
      <StatusPanel
        state="error"
        title="暂时无法确认档案访问权限"
        description={state.message}
      />
    );
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能查看自己的 ProfileVersion、授权状态和保存记录。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  return <ProfileArchive />;
}

export function AccountProfilesSurface() {
  return (
    <AccountSessionBoundary>
      <div className={styles.accountPage}>
        <AppPageHeader
          description="档案版本只来自服务端确认事实；没有登录或授权时，不展示出生资料。"
          title="受测人档案"
        />
        <section aria-label="个人中心 · 档案" className={styles.accountPanel}>
          <AccountProfilesContent />
        </section>
      </div>
    </AccountSessionBoundary>
  );
}
