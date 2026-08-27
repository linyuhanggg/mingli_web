"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { adoptCsrfToken, ApiError, loginWithPassword } from "@/lib/api";
import { destinationAfterLogin } from "@/lib/login-continue";

import { useOptionalAccountSession } from "./account-session-context";
import authStyles from "./auth-shell.module.css";
import styles from "./surfaces/secondary-surfaces.module.css";

function channelFor(destination: string): "phone" | "email" {
  return destination.includes("@") ? "email" : "phone";
}

export function PasswordLoginForm() {
  const router = useRouter();
  const accountSession = useOptionalAccountSession();
  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedDestination = destination.trim();
    if (!normalizedDestination || password.length < 8) {
      setError("请输入手机或邮箱，以及至少八位密码。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const session = await loginWithPassword({
        channel: channelFor(normalizedDestination),
        destination: normalizedDestination,
        password,
      });
      adoptCsrfToken(session.csrf_token);
      if (accountSession) {
        void accountSession.refresh({ force: true });
      }
      router.replace(destinationAfterLogin());
    } catch (reason) {
      const invalidCredentials =
        (reason instanceof ApiError && reason.status === 401)
        || (reason instanceof Error && reason.message === "Invalid credentials");
      setError(
        invalidCredentials
          ? "账号或密码不正确。"
          : "登录服务暂时不可用，请稍后重试。",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-busy={busy}
      aria-describedby="password-login-help"
      aria-label="密码主登录表单"
      className={styles.form}
      onSubmit={submit}
      noValidate
    >
      <div className={styles.fields}>
        <div className={styles.field}>
          <label htmlFor="password-login-identity">手机或邮箱</label>
          <input
            id="password-login-identity"
            autoComplete="username"
            disabled={busy}
            onChange={(event) => setDestination(event.target.value)}
            spellCheck={false}
            type="text"
            value={destination}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="password-login-password">密码</label>
          <input
            id="password-login-password"
            autoComplete="current-password"
            disabled={busy}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            value={password}
          />
        </div>
      </div>
      <p className={styles.field} id="password-login-help">
        密码不会保存在这台设备上。
      </p>
      {error ? (
        <p className={styles.disabledReason} role="alert">
          {error}
        </p>
      ) : null}
      <button className={authStyles.submit} disabled={busy} type="submit">
        {busy ? "正在登录…" : "登录"}
      </button>
    </form>
  );
}
