"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import {
  adoptCsrfToken,
  ApiError,
  registerWithOtp,
  requestOtp,
} from "@/lib/api";
import { CURRENT_POLICY_VERSION } from "@/lib/policy";

import { useOptionalAccountSession } from "./account-session-context";
import styles from "./surfaces/secondary-surfaces.module.css";

function channelFor(destination: string): "phone" | "email" {
  return destination.includes("@") ? "email" : "phone";
}

export function RegistrationForm() {
  const router = useRouter();
  const accountSession = useOptionalAccountSession();
  const [destination, setDestination] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [developmentCode, setDevelopmentCode] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
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

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError("请输入六位数字验证码。");
      return;
    }
    if (password.length < 8) {
      setError("密码至少需要八位。");
      return;
    }
    if (password !== confirmation) {
      setError("两次输入的密码不一致。");
      return;
    }
    if (!privacyAccepted || !termsAccepted) {
      setError("请分别阅读并同意隐私政策和服务条款。");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const session = await registerWithOtp({
        challenge_id: challengeId,
        code,
        password,
        policy_version: CURRENT_POLICY_VERSION,
      });
      adoptCsrfToken(session.csrf_token);
      if (accountSession) {
        void accountSession.refresh({ force: true });
      }
      router.replace("/account");
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        setError("该身份已经注册，请直接登录或找回密码。");
      } else {
        setError("注册服务暂时不可用，请稍后重试。");
      }
    } finally {
      setBusy(false);
    }
  }

  if (challengeId) {
    const canSubmit = privacyAccepted && termsAccepted && !busy;
    return (
      <form
        aria-busy={busy}
        aria-describedby="registration-consent-help"
        aria-label="验证并注册"
        className={styles.form}
        onSubmit={register}
        noValidate
      >
        {developmentCode ? (
          <p className={styles.field}>
            调试码（仅开发/测试环境）：{developmentCode}
          </p>
        ) : null}
        <p className={styles.field} id="registration-consent-help">
          注册会保存当前开发预览政策版本；两份政策必须分别同意。
        </p>
        <div className={styles.fields}>
          <div className={styles.field}>
            <label htmlFor="registration-code">验证码</label>
            <input
              id="registration-code"
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
            <label htmlFor="registration-password">设置密码</label>
            <input
              id="registration-password"
              autoComplete="new-password"
              disabled={busy}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="registration-confirm">确认密码</label>
            <input
              id="registration-confirm"
              autoComplete="new-password"
              disabled={busy}
              onChange={(event) => setConfirmation(event.target.value)}
              type="password"
              value={confirmation}
            />
          </div>
          <label>
            <input
              checked={privacyAccepted}
              disabled={busy}
              onChange={(event) => setPrivacyAccepted(event.target.checked)}
              type="checkbox"
            />
            我已阅读并同意隐私政策
          </label>
          <label>
            <input
              checked={termsAccepted}
              disabled={busy}
              onChange={(event) => setTermsAccepted(event.target.checked)}
              type="checkbox"
            />
            我已阅读并同意服务条款
          </label>
        </div>
        {error ? <p className={styles.disabledReason} role="alert">{error}</p> : null}
        <button disabled={!canSubmit} type="submit">
          {busy ? "正在注册…" : "注册并登录"}
        </button>
      </form>
    );
  }

  return (
    <form
      aria-busy={busy}
      aria-describedby="registration-destination-help"
      aria-label="发送注册验证码"
      className={styles.form}
      onSubmit={sendCode}
      noValidate
    >
      <div className={styles.field}>
        <label htmlFor="registration-destination">手机或邮箱</label>
        <input
          id="registration-destination"
          autoComplete="username"
          disabled={busy}
          onChange={(event) => setDestination(event.target.value)}
          spellCheck={false}
          type="text"
          value={destination}
        />
        <p id="registration-destination-help">
          OTP 核验后才会创建身份，并继续设置密码和记录政策版本。
        </p>
      </div>
      {error ? <p className={styles.disabledReason} role="alert">{error}</p> : null}
      <button disabled={busy} type="submit">
        {busy ? "正在发送…" : "发送验证码"}
      </button>
    </form>
  );
}
