"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import {
  adoptCsrfToken,
  ApiError,
  recoverPassword,
  requestOtp,
} from "@/lib/api";

import { useOptionalAccountSession } from "./account-session-context";
import styles from "./surfaces/secondary-surfaces.module.css";

function channelFor(destination: string): "phone" | "email" {
  return destination.includes("@") ? "email" : "phone";
}

export function PasswordRecoveryForm() {
  const router = useRouter();
  const accountSession = useOptionalAccountSession();
  const [destination, setDestination] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [developmentCode, setDevelopmentCode] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedDestination = destination.trim();
    if (!normalizedDestination) {
      setError("请输入手机或邮箱。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const challenge = await requestOtp({
        channel: channelFor(normalizedDestination),
        destination: normalizedDestination,
      });
      setChallengeId(challenge.challenge_id);
      setDevelopmentCode(challenge.development_code ?? "");
    } catch {
      setError("验证码发送失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  async function submitRecovery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError("请输入六位数字验证码。");
      return;
    }
    if (password.length < 8) {
      setError("新密码至少需要八位。");
      return;
    }
    if (password !== confirmation) {
      setError("两次输入的新密码不一致。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const session = await recoverPassword({
        challenge_id: challengeId,
        code,
        password,
      });
      adoptCsrfToken(session.csrf_token);
      if (accountSession) {
        void accountSession.refresh({ force: true });
      }
      router.replace("/account");
    } catch (reason) {
      const invalid = reason instanceof ApiError && reason.status === 401;
      setError(
        invalid
          ? "账号或验证码不正确。"
          : "找回服务暂时不可用，请稍后重试。",
      );
    } finally {
      setBusy(false);
    }
  }

  if (challengeId) {
    return (
      <form
        aria-busy={busy}
        aria-describedby="password-recovery-code-help"
        aria-label="验证并重设密码"
        className={styles.form}
        onSubmit={submitRecovery}
        noValidate
      >
        {developmentCode ? (
          <p className={styles.field}>
            调试码（仅开发/测试环境）：{developmentCode}
          </p>
        ) : null}
        <p className={styles.field} id="password-recovery-code-help">
          验证码已发送；找回成功会撤销其他设备会话。
        </p>
        <div className={styles.fields}>
          <div className={styles.field}>
            <label htmlFor="password-recovery-code">验证码</label>
            <input
              id="password-recovery-code"
              autoComplete="one-time-code"
              disabled={busy}
              inputMode="numeric"
              maxLength={6}
              onChange={(event) => setCode(event.target.value)}
              pattern="[0-9]{6}"
              type="text"
              value={code}
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="password-recovery-password">新密码</label>
            <input
              id="password-recovery-password"
              autoComplete="new-password"
              disabled={busy}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="password-recovery-confirm">确认新密码</label>
            <input
              id="password-recovery-confirm"
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
          {busy ? "正在重设…" : "重设密码并登录"}
        </button>
      </form>
    );
  }

  return (
    <form
      aria-busy={busy}
      aria-describedby="password-recovery-destination-help"
      aria-label="发送找回验证码"
      className={styles.form}
      onSubmit={sendCode}
      noValidate
    >
      <div className={styles.field}>
        <label htmlFor="password-recovery-destination">手机或邮箱</label>
        <input
          id="password-recovery-destination"
          autoComplete="username"
          disabled={busy}
          onChange={(event) => setDestination(event.target.value)}
          spellCheck={false}
          type="text"
          value={destination}
        />
        <p id="password-recovery-destination-help">
          只会向已经验证过的身份发送验证码，不会因为找回请求创建新账号。
        </p>
      </div>
      {error ? <p className={styles.disabledReason} role="alert">{error}</p> : null}
      <button disabled={busy} type="submit">
        {busy ? "正在发送…" : "发送验证码"}
      </button>
    </form>
  );
}
