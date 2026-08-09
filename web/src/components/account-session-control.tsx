"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ApiError,
  getAccount,
  logoutCurrentDevice,
  type AccountResponse,
  type LoginIdentitySummary,
} from "@/lib/api";

import surface from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";

import styles from "./account-session-control.module.css";


type ProbeState =
  | { status: "checking" }
  | { status: "signedOut" }
  | { status: "error"; message: string }
  | { status: "signedIn"; account: AccountResponse };

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "服务暂时不可用，请稍后重试。";
}

function providerLabel(identity: LoginIdentitySummary): string {
  return identity.provider === "email" ? "邮箱" : "手机号";
}

export default function AccountSessionControl() {
  const router = useRouter();
  const [probe, setProbe] = useState<ProbeState>({ status: "checking" });
  const [probeAttempt, setProbeAttempt] = useState(0);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getAccount()
      .then((account) => {
        if (!cancelled) {
          setProbe({ status: "signedIn", account });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          setProbe({ status: "signedOut" });
        } else {
          setProbe({ status: "error", message: errorMessage(error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [probeAttempt]);

  function handleProbeRetry() {
    setProbe({ status: "checking" });
    setProbeAttempt((attempt) => attempt + 1);
  }

  async function handleLogout() {
    setLogoutBusy(true);
    setLogoutError("");
    try {
      await logoutCurrentDevice();
      router.replace("/");
    } catch (error) {
      setLogoutError(`退出失败：${errorMessage(error)}`);
      setLogoutBusy(false);
    }
  }

  if (probe.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在读取账户状态…"
        description="正在确认当前设备会话，请稍候。"
      />
    );
  }

  if (probe.status === "signedOut") {
    return (
      <StatusPanel
        state="disabled"
        title="身份与设备"
        description="当前未登录；邮箱验证码登录后，这里会显示已绑定身份，并可以撤销当前设备。"
      />
    );
  }

  if (probe.status === "error") {
    return (
      <div className={styles.cardStack}>
        <StatusPanel
          state="error"
          title="无法读取账户状态"
          description={probe.message}
        />
        <div className={styles.retryRow}>
          <button
            className={surface.secondaryButton}
            type="button"
            onClick={handleProbeRetry}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <section
      className={surface.paper}
      aria-labelledby="device-session-title"
    >
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="device-session-title">身份与设备</h2>
          <p>当前设备已登录；退出后需要重新验证邮箱才能回到这里。</p>
        </div>
      </div>
      {probe.account.identities.length > 0 ? (
        <ul className={surface.accountList} aria-label="已绑定登录身份">
          {probe.account.identities.map((identity) => (
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
        >
          {logoutBusy ? "正在退出…" : "退出当前设备"}
        </button>
      </div>
    </section>
  );
}
