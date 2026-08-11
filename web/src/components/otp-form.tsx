"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { adoptCsrfToken, getCsrfToken } from "@/lib/api";

import { useOptionalAccountSession } from "./account-session-context";
import styles from "./otp-form.module.css";


type Phase =
  | "bootstrapping"
  | "unavailable"
  | "destination"
  | "code"
  | "authenticated";

type OtpChallenge = {
  challenge_id: string;
  development_code?: string;
};

type DeviceSession = {
  csrf_token: string;
};

type Problem = {
  title?: string;
};

type DestinationFormValues = {
  destination: string;
};

type CodeFormValues = {
  code: string;
};

const emailAddress = z.email();
const emailSchema = z.object({
  destination: z.string().refine(
    (value) => emailAddress.safeParse(value.trim()).success,
    "请输入有效的邮箱地址",
  ),
});

const verificationCodeSchema = z.object({
  code: z.string().regex(/^\d{6}$/, "请输入六位数字验证码"),
});

async function requestJson<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, credentials: "include" });
  let body: (T & Problem) | null = null;

  if (response.headers.get("content-type")?.includes("application/json")) {
    try {
      body = (await response.json()) as T & Problem;
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    throw new Error(body?.title ?? "服务暂时不可用，请稍后重试");
  }
  if (!body) {
    throw new Error("服务器响应异常，请稍后重试");
  }
  return body as T;
}

export function OtpForm() {
  const router = useRouter();
  const accountSession = useOptionalAccountSession();
  const [phase, setPhase] = useState<Phase>("bootstrapping");
  const [csrfToken, setCsrfToken] = useState("");
  const [challenge, setChallenge] = useState<OtpChallenge | null>(null);
  const [submittedDestination, setSubmittedDestination] = useState("");
  const [deliveryAttempt, setDeliveryAttempt] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [bootstrapAttempt, setBootstrapAttempt] = useState(0);
  const destinationForm = useForm<DestinationFormValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: { destination: "" },
  });
  const codeForm = useForm<CodeFormValues>({
    resolver: zodResolver(verificationCodeSchema),
    defaultValues: { code: "" },
  });

  useEffect(() => {
    if (phase === "code") {
      codeForm.setFocus("code");
    }
  }, [phase, codeForm]);

  useEffect(() => {
    let active = true;
    getCsrfToken()
      .then((token) => {
        if (!active) return;
        setCsrfToken(token);
        setPhase("destination");
      })
      .catch(() => {
        if (!active) return;
        setPhase("unavailable");
        setError("登录服务暂时不可用，请稍后重试。");
      });
    return () => {
      active = false;
    };
  }, [bootstrapAttempt]);

  function retryBootstrap() {
    setError("");
    setPhase("bootstrapping");
    setBootstrapAttempt((attempt) => attempt + 1);
  }

  async function sendCodeTo(destination: string) {
    const trimmedDestination = destination.trim();
    setBusy(true);
    setError("");
    try {
      const requested = await requestJson<OtpChallenge>("/api/v1/auth/otp/request", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          channel: "email",
          destination: trimmedDestination,
        }),
      });
      setSubmittedDestination(trimmedDestination);
      setDeliveryAttempt((attempt) => attempt + 1);
      setChallenge(requested);
      codeForm.reset({ code: "" });
      setPhase("code");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "验证码发送失败";
      if (phase === "code") {
        setError(message);
      } else {
        destinationForm.setError(
          "destination",
          { type: "server", message },
          { shouldFocus: true },
        );
      }
    } finally {
      setBusy(false);
    }
  }

  function changeDestination() {
    setChallenge(null);
    setSubmittedDestination("");
    setDeliveryAttempt(0);
    codeForm.reset({ code: "" });
    setError("");
    setPhase("destination");
    setTimeout(() => {
      destinationForm.setFocus("destination");
    }, 0);
  }

  async function verifyCode({ code }: CodeFormValues) {
    if (!challenge) return;
    setBusy(true);
    setError("");
    try {
      const verified = await requestJson<DeviceSession>("/api/v1/auth/otp/verify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ challenge_id: challenge.challenge_id, code }),
      });
      adoptCsrfToken(verified.csrf_token);
      setPhase("authenticated");
      if (accountSession) {
        await accountSession.refresh();
      }
      router.replace("/app");
    } catch (reason) {
      codeForm.setError(
        "code",
        {
          type: "server",
          message: reason instanceof Error ? reason.message : "验证码验证失败",
        },
        { shouldFocus: true },
      );
    } finally {
      setBusy(false);
    }
  }

  if (phase === "authenticated") {
    return (
      <section className={styles.form} aria-live="polite">
        <p className={styles.success}>登录成功</p>
        <p className={styles.transition}>
          正在进入 /app…设备会话已建立，不会再创建游客身份。
        </p>
      </section>
    );
  }

  return (
    <section className={styles.form} aria-busy={busy || phase === "bootstrapping"}>
      <p className={styles.status} role="status">
        {phase === "bootstrapping"
          ? "正在建立安全会话…"
          : phase === "unavailable"
            ? "安全会话暂未建立"
            : "安全会话已建立"}
      </p>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      {phase === "unavailable" ? (
        <button className={styles.submit} type="button" onClick={retryBootstrap}>
          重新连接
        </button>
      ) : null}
      <ul
        className={styles.methods}
        aria-label="登录方式"
        hidden={phase === "unavailable"}
      >
        <li className={styles.methodActive}>
          <strong>邮箱验证码</strong>
          <span>当前开放</span>
        </li>
        <li className={styles.methodLocked}>
          <strong>手机号验证码</strong>
          <span>稍后开放</span>
        </li>
      </ul>

      {phase === "destination" || phase === "bootstrapping" ? (
        <form
          onSubmit={destinationForm.handleSubmit(({ destination }) =>
            sendCodeTo(destination)
          )}
          noValidate
          aria-label="发送邮箱验证码"
        >
          <div className={styles.field}>
            <label htmlFor="otp-destination">邮箱地址</label>
            <input
              id="otp-destination"
              type="email"
              autoComplete="email"
              spellCheck={false}
              disabled={phase === "bootstrapping" || busy}
              aria-invalid={Boolean(destinationForm.formState.errors.destination)}
              aria-describedby={
                destinationForm.formState.errors.destination
                  ? "otp-destination-error"
                  : "otp-destination-help"
              }
              required
              {...destinationForm.register("destination")}
            />
            <p className={styles.hint} id="otp-destination-help">
              验证码将发送到该邮箱，不会对外公开。
            </p>
            {destinationForm.formState.errors.destination ? (
              <p
                className={styles.fieldError}
                id="otp-destination-error"
                role="alert"
              >
                {destinationForm.formState.errors.destination.message}
              </p>
            ) : null}
          </div>
          <button className={styles.submit} type="submit" disabled={busy || !csrfToken}>
            {busy ? "正在发送…" : "发送验证码"}
          </button>
        </form>
      ) : null}

      {phase === "code" && challenge ? (
        <form onSubmit={codeForm.handleSubmit(verifyCode)} noValidate aria-label="验证登录">
          {challenge.development_code ? (
            <p className={styles.hint}>调试码（仅开发/测试环境）：{challenge.development_code}</p>
          ) : null}
          <p className={styles.codeMeta} role="status">
            {deliveryAttempt > 1
              ? `验证码已重新发送（第 ${deliveryAttempt} 次）至 ${submittedDestination}。`
              : `验证码已发送至 ${submittedDestination}。`}
            可以重新发送，或更换邮箱。
          </p>
          <div className={styles.field}>
            <label htmlFor="otp-code">六位验证码</label>
            <input
              id="otp-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              spellCheck={false}
              pattern="[0-9]{6}"
              maxLength={6}
              aria-invalid={Boolean(codeForm.formState.errors.code)}
              aria-describedby={
                codeForm.formState.errors.code ? "otp-code-error" : "otp-code-help"
              }
              required
              {...codeForm.register("code")}
            />
            <p className={styles.hint} id="otp-code-help">
              验证码为六位数字；验证成功即建立当前设备会话。
            </p>
            {codeForm.formState.errors.code ? (
              <p className={styles.fieldError} id="otp-code-error" role="alert">
                {codeForm.formState.errors.code.message}
              </p>
            ) : null}
          </div>
          <button className={styles.submit} type="submit" disabled={busy}>
            {busy ? "正在验证…" : "验证并登录"}
          </button>
          <div className={styles.actionRow}>
            <button
              className={styles.secondary}
              type="button"
              disabled={busy}
              onClick={() => sendCodeTo(submittedDestination)}
            >
              {busy ? "正在发送…" : "重新发送验证码"}
            </button>
            <button
              className={styles.secondary}
              type="button"
              disabled={busy}
              onClick={changeDestination}
            >
              更换邮箱
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
