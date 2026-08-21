"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { adminFetch, type AdminSessionResponse } from "@/lib/api";
import { EnvBadge } from "@/components/env-badge";
import { Button, Field } from "@/components/ui";
import ui from "@/components/ui.module.css";

type LoginError = {
  fieldsInvalid: boolean;
  message: string;
};

function getLoginError(status: number, title: string): LoginError {
  const normalizedTitle = title.trim().toLowerCase();

  if (status === 401 || normalizedTitle.includes("invalid email or password")) {
    return { fieldsInvalid: true, message: "工作邮箱或密码不正确。" };
  }
  if (status === 400 || normalizedTitle === "invalid request") {
    return { fieldsInvalid: true, message: "请检查工作邮箱和密码后重试。" };
  }
  if (normalizedTitle.includes("too many login attempts")) {
    return { fieldsInvalid: false, message: "尝试次数过多，请稍后再试。" };
  }
  if (status === 0 || status >= 500 || title.includes("运营平台暂时不可用")) {
    return { fieldsInvalid: false, message: "登录服务暂时不可用，请稍后重试。" };
  }
  return { fieldsInvalid: false, message: "登录未能完成，请稍后重试。" };
}

export default function LoginPage() {
  const router = useRouter();
  const emailInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<LoginError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!error) return;
    if (error.fieldsInvalid) {
      emailInputRef.current?.focus();
      return;
    }
    formRef.current?.querySelector<HTMLButtonElement>('button[type="submit"]')?.focus();
  }, [error]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const result = await adminFetch<AdminSessionResponse>("/api/v1/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setPending(false);
    if (!result.ok) {
      setError(getLoginError(result.status, result.title));
      return;
    }
    router.replace("/");
  }

  return (
    <>
      <a
        className={ui.loginSkip}
        href="#admin-login-main"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("admin-login-main")?.focus();
        }}
      >
        跳到主要内容
      </a>
      <main id="admin-login-main" className={ui.loginWrap} tabIndex={-1}>
      <div className={`${ui.paper} ${ui.loginCard}`}>
        <div className={ui.loginHead}>
          <EnvBadge />
          <h1 id="admin-login-title">员工登录</h1>
          <p className={ui.muted}>运营台仅限员工。与用户账号分离。</p>
        </div>
        <form
          ref={formRef}
          aria-busy={pending || undefined}
          aria-labelledby="admin-login-title"
          className={ui.form}
          onSubmit={onSubmit}
        >
          <Field label="工作邮箱" required>
            <input
              ref={emailInputRef}
              name="email"
              type="email"
              autoComplete="username"
              spellCheck={false}
              aria-describedby={error?.fieldsInvalid ? "admin-login-error" : undefined}
              aria-invalid={error?.fieldsInvalid || undefined}
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError(null);
              }}
            />
          </Field>
          <Field label="密码" required>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              aria-describedby={error?.fieldsInvalid ? "admin-login-error" : undefined}
              aria-invalid={error?.fieldsInvalid || undefined}
              required
              minLength={8}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setError(null);
              }}
            />
          </Field>
          {error ? (
            <p className={ui.alert} id="admin-login-error" role="alert">
              {error.message}
            </p>
          ) : null}
          <Button type="submit" loading={pending} style={{ minHeight: "var(--target-submit)" }}>
            {pending ? "登录中…" : "进入运营台"}
          </Button>
        </form>
      </div>
      </main>
    </>
  );
}
