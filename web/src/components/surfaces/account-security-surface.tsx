"use client";

import { useState } from "react";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import { revokeAllSessions } from "@/lib/api";

import surface from "../app-surface.module.css";
import { StatusPanel } from "../status-panel";
import { SecondaryStatus } from "./secondary-status";
import secondary from "./secondary-surfaces.module.css";

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "设备会话暂时无法管理，请稍后重试。";
}

function SecurityContent() {
  const { state, markSignedOut } = useAccountSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.status === "checking") {
    return <StatusPanel state="loading" title="正在确认账户…" description="正在确认设备会话访问权限。" />;
  }

  if (state.status === "error") {
    return <StatusPanel state="error" title="无法确认账户" description={state.message} />;
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能查看已验证身份并撤销所有设备会话。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  async function handleRevokeAll() {
    if (!window.confirm("这会退出所有设备，确认继续吗？")) return;
    setBusy(true);
    setError(null);
    try {
      await revokeAllSessions();
      markSignedOut();
    } catch (nextError) {
      setError(readableError(nextError));
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="account-security-title" className={surface.paper}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="account-security-title">设备安全</h2>
          <p>撤销后，当前设备也会退出。</p>
        </div>
      </div>
      <ul aria-label="已验证身份" className={surface.accountList}>
        {state.account.identities.map((identity) => (
          <li key={identity.id}>
            <strong>{identity.provider === "email" ? "邮箱" : "手机号"}</strong>
            <span>{identity.masked_destination}</span>
          </li>
        ))}
      </ul>
      <p>撤销所有设备会话后，当前设备也会退出，需要重新验证才能访问账户。</p>
      {error ? <p role="alert">{error}</p> : null}
      <div className={secondary.actionRow}>
        <button
          className={surface.button}
          disabled={busy}
          onClick={() => void handleRevokeAll()}
          type="button"
        >
          {busy ? "正在撤销…" : "撤销所有设备会话"}
        </button>
      </div>
    </section>
  );
}

export function AccountSecuritySurface() {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="查看已验证身份，并可以退出全部设备。" title="设备安全">
        <SecurityContent />
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
