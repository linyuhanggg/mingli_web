"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { adminFetch, type AdminSessionResponse } from "@/lib/api";
import { EnvBadge } from "@/components/env-badge";
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
    <div className={ui.loginWrap}>
      <div className={`${ui.paper} ${ui.loginCard}`}>
        <div className={ui.loginHead}>
          <div style={{ marginBottom: "0.75rem" }}>
            <EnvBadge />
          </div>
          <h1>员工登录</h1>
          <p className={ui.muted}>运营台仅限员工。与用户账号分离。</p>
        </div>
        <form className={ui.form} onSubmit={onSubmit}>
          <div className={ui.field}>
            <label htmlFor="email">工作邮箱</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className={ui.field}>
            <label htmlFor="password">密码</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          {error ? (
            <p className={ui.alert} role="alert">
              {error}
            </p>
          ) : null}
          <button className={`${ui.button} ${ui.primary}`} type="submit" disabled={pending}>
            {pending ? "登录中…" : "进入运营台"}
          </button>
        </form>
      </div>
    </div>
  );
}
