"use client";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import { ProfileForm } from "@/components/profile-form";
import { StatusPanel } from "@/components/status-panel";

import { SecondaryStatus } from "./secondary-status";
import styles from "./secondary-surfaces.module.css";

function AccountNewProfileContent() {
  const { state } = useAccountSession();

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在确认档案访问权限"
        description="正在确认账户。"
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
        description="登录后才能建立并保存档案。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  return <ProfileForm />;
}

export function AccountNewProfileSurface() {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="为档案命名，并核对这份出生资料。" title="新建档案">
        <section aria-label="新建档案" className={styles.accountPanel}>
          <AccountNewProfileContent />
        </section>
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
