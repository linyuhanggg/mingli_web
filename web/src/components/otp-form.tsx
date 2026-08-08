"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import styles from "./otp-form.module.css";


type Channel = "phone" | "email";
type Phase =
  | "bootstrapping"
  | "unavailable"
  | "destination"
  | "code"
  | "authenticated";

type GuestSession = {
  csrf_token: string;
};

type OtpChallenge = {
  challenge_id: string;
  development_code?: string;
};

type DeviceSession = {
  user_id: string;
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

const mainlandPhoneSchema = z.object({
  destination: z.string().refine((value) => {
    const digits = value.replace(/\D/g, "");
    const localDigits = digits.startsWith("86") && digits.length === 13
      ? digits.slice(2)
      : digits;
    return /^1[3-9]\d{9}$/.test(localDigits);
  }, "请输入有效的中国大陆手机号"),
});

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
  const [phase, setPhase] = useState<Phase>("bootstrapping");
  const [channel, setChannel] = useState<Channel>("phone");
  const [csrfToken, setCsrfToken] = useState("");
  const [challenge, setChallenge] = useState<OtpChallenge | null>(null);
  const [session, setSession] = useState<DeviceSession | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [bootstrapAttempt, setBootstrapAttempt] = useState(0);
  const destinationForm = useForm<DestinationFormValues>({
    resolver: zodResolver(channel === "phone" ? mainlandPhoneSchema : emailSchema),
    defaultValues: { destination: "" },
  });
  const codeForm = useForm<CodeFormValues>({
    resolver: zodResolver(verificationCodeSchema),
    defaultValues: { code: "" },
  });

  useEffect(() => {
    let active = true;
    requestJson<GuestSession>("/api/v1/guest-sessions", { method: "POST" })
      .then((guest) => {
        if (!active) return;
        setCsrfToken(guest.csrf_token);
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

  function chooseChannel(nextChannel: Channel) {
    setChannel(nextChannel);
    destinationForm.reset({ destination: "" });
    codeForm.reset({ code: "" });
    setChallenge(null);
    setError("");
    setPhase("destination");
  }

  async function sendCode({ destination }: DestinationFormValues) {
    setBusy(true);
    setError("");
    try {
      const requested = await requestJson<OtpChallenge>("/api/v1/auth/otp/request", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ channel, destination }),
      });
      setChallenge(requested);
      codeForm.reset({ code: "" });
      setPhase("code");
    } catch (reason) {
      destinationForm.setError(
        "destination",
        {
          type: "server",
          message: reason instanceof Error ? reason.message : "验证码发送失败",
        },
        { shouldFocus: true },
      );
    } finally {
      setBusy(false);
    }
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
      setCsrfToken(verified.csrf_token);
      setSession(verified);
      setPhase("authenticated");
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

  if (phase === "authenticated" && session) {
    return (
      <section className={styles.form} aria-live="polite">
        <p className={styles.success}>登录成功</p>
        <p>内部 User 是账户根，手机号或邮箱只是可绑定的登录身份。</p>
        <p className={styles.accountRoot}>User ID：{session.user_id}</p>
      </section>
    );
  }

  return (
    <section className={styles.form}>
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
      <div className={styles.tabs} aria-label="验证码方式" hidden={phase === "unavailable"}>
        <button
          type="button"
          aria-pressed={channel === "phone"}
          disabled={phase === "bootstrapping" || busy}
          onClick={() => chooseChannel("phone")}
        >
          手机号验证码
        </button>
        <button
          type="button"
          aria-pressed={channel === "email"}
          disabled={phase === "bootstrapping" || busy}
          onClick={() => chooseChannel("email")}
        >
          邮箱验证码
        </button>
      </div>

      {phase === "destination" || phase === "bootstrapping" ? (
        <form onSubmit={destinationForm.handleSubmit(sendCode)} noValidate>
          <div className={styles.field}>
            <label htmlFor="otp-destination">
              {channel === "phone" ? "中国大陆手机号" : "邮箱地址"}
            </label>
            <input
              id="otp-destination"
              type={channel === "phone" ? "tel" : "email"}
              autoComplete={channel === "phone" ? "tel" : "email"}
              disabled={phase === "bootstrapping" || busy}
              aria-invalid={Boolean(destinationForm.formState.errors.destination)}
              aria-describedby={
                destinationForm.formState.errors.destination
                  ? "otp-destination-error"
                  : undefined
              }
              required
              {...destinationForm.register("destination")}
            />
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
        <form onSubmit={codeForm.handleSubmit(verifyCode)} noValidate>
          {challenge.development_code ? (
            <p className={styles.hint}>本地测试验证码：{challenge.development_code}</p>
          ) : null}
          <div className={styles.field}>
            <label htmlFor="otp-code">六位验证码</label>
            <input
              id="otp-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              aria-invalid={Boolean(codeForm.formState.errors.code)}
              aria-describedby={
                codeForm.formState.errors.code ? "otp-code-error" : undefined
              }
              required
              {...codeForm.register("code")}
            />
            {codeForm.formState.errors.code ? (
              <p className={styles.fieldError} id="otp-code-error" role="alert">
                {codeForm.formState.errors.code.message}
              </p>
            ) : null}
          </div>
          <button className={styles.submit} type="submit" disabled={busy}>
            {busy ? "正在验证…" : "验证并登录"}
          </button>
        </form>
      ) : null}
    </section>
  );
}
