"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  logoutCurrentDevice,
  type LoginIdentitySummary,
} from "@/lib/api";

import {
  AccountSessionBoundary,
  useAccountSession,
} from "./account-session-context";
import surface from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";

import styles from "./account-session-control.module.css";


function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "服务暂时不可用，请稍后重试。";
}

function providerLabel(identity: LoginIdentitySummary): string {
  return identity.provider === "email" ? "邮箱" : "手机号";
}

function AccountSessionControlContent() {
  const router = useRouter();
  const { state, refresh, markSignedOut } = useAccountSession();
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    setLogoutBusy(true);
    setLogoutError("");
    try {
      await logoutCurrentDevice();
      markSignedOut();
      router.replace("/");
    } catch (error) {
      setLogoutError(`退出失败：${errorMessage(error)}`);
      setLogoutBusy(false);
    }
  }

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在读取账户状态…"
        description="正在确认登录状态，请稍候。"
      />
    );
  }

  if (state.status === "signedOut") {
    return (
      <StatusPanel
        state="disabled"
        title="身份与设备"
        description="当前设备尚未登录。OTP 快捷登录后，这里会显示已绑定身份，并可以撤销当前设备。"
      />
    );
  }

  if (state.status === "error") {
    return (
      <div className={styles.cardStack}>
        <StatusPanel
          state="error"
          title="无法读取账户状态"
          description="读取失败，请重试"
        />
        <div className={styles.retryRow}>
          <button
            className={surface.secondaryButton}
            type="button"
            onClick={() => void refresh()}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className={surface.paper} aria-labelledby="device-session-title">
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="device-session-title">身份与设备</h2>
          <p>当前设备已登录；退出后需要重新验证邮箱才能回到私人档案。</p>
        </div>
      </div>
      {state.account.identities.length > 0 ? (
        <ul className={surface.accountList} aria-label="已绑定登录身份">
          {state.account.identities.map((identity) => (
            <li key={identity.id}>
              <strong>{providerLabel(identity)}</strong>
              <span>{identity.masked_destination}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.noIdentity}>还没有已绑定的登录身份。</p>
      )}
      <p className={styles.deviceState}>
        <span className={surface.stateTag} data-state="success">
          当前设备已登录
        </span>
      </p>
      {logoutError ? (
        <p className={styles.logoutError} role="alert">
          {logoutError}
        </p>
      ) : null}
      <div className={styles.logoutRow}>
        <button
          className={surface.button}
          type="button"
          onClick={handleLogout}
          disabled={logoutBusy}
          aria-describedby={logoutBusy ? "logout-busy-reason" : undefined}
        >
          {logoutBusy ? "正在退出…" : "退出当前设备"}
        </button>
        {logoutBusy ? (
          <p className={styles.busyReason} id="logout-busy-reason" role="status">
            正在退出，请稍候。
          </p>
        ) : null}
      </div>
    </section>
  );
}

export default function AccountSessionControl() {
  return (
    <AccountSessionBoundary>
      <AccountSessionControlContent />
    </AccountSessionBoundary>
  );
}
