"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { adminFetch, type AdminSessionResponse } from "@/lib/api";
import { EnvBadge } from "@/components/env-badge";
import { Button, Field } from "@/components/ui";
import ui from "@/components/ui.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
      setError(result.title);
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
          <div style={{ marginBottom: "0.75rem" }}>
            <EnvBadge />
          </div>
          <h1 id="admin-login-title">员工登录</h1>
          <p className={ui.muted}>运营台仅限员工。与用户账号分离。</p>
        </div>
        <form aria-labelledby="admin-login-title" className={ui.form} onSubmit={onSubmit}>
          <Field label="工作邮箱" required>
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>
          <Field label="密码" required>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          {error ? (
            <p className={ui.alert} role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" loading={pending}>
            {pending ? "登录中…" : "进入运营台"}
          </Button>
        </form>
      </div>
      </main>
    </>
  );
}
