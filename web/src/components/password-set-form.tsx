"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, setPassword } from "@/lib/api";

import styles from "./surfaces/secondary-surfaces.module.css";

export function PasswordSetForm() {
  const router = useRouter();
  const [password, setPasswordValue] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setError("密码至少需要八位。");
      return;
    }
    if (password !== confirmation) {
      setError("两次输入的密码不一致。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      await setPassword(password);
      router.replace("/account");
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? "请先登录后再设置密码。"
          : "密码服务暂时不可用，请稍后重试。",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-busy={busy}
      aria-describedby="password-set-help"
      aria-label="设置密码"
      className={styles.form}
      onSubmit={submit}
      noValidate
    >
      <p className={styles.field} id="password-set-help">
        只有当前设备已验证身份时才能设置密码；服务端只保存不可逆哈希。
      </p>
      <div className={styles.fields}>
        <div className={styles.field}>
          <label htmlFor="password-set-value">新密码</label>
          <input
            id="password-set-value"
            autoComplete="new-password"
            disabled={busy}
            onChange={(event) => setPasswordValue(event.target.value)}
            type="password"
            value={password}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="password-set-confirm">确认新密码</label>
          <input
            id="password-set-confirm"
            autoComplete="new-password"
            disabled={busy}
            onChange={(event) => setConfirmation(event.target.value)}
            type="password"
            value={confirmation}
          />
        </div>
      </div>
      {error ? <p className={styles.disabledReason} role="alert">{error}</p> : null}
      <button disabled={busy} type="submit">
        {busy ? "正在保存…" : "保存密码"}
      </button>
    </form>
  );
}
