"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { adminFetch, type AdminMeResponse } from "@/lib/api";
import { EnvBadge } from "./env-badge";
import styles from "./admin-shell.module.css";
import ui from "./ui.module.css";

const NAV = [
  { href: "/", label: "总览" },
  { href: "/users", label: "用户档案" },
  { href: "/orders", label: "订单支付" },
  { href: "/refunds", label: "退款审批" },
  { href: "/readings", label: "解读任务" },
  { href: "/audit", label: "审计日志" },
] as const;

export function AdminShell({
  title,
  duty,
  children,
}: {
  title: string;
  duty: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [staff, setStaff] = useState<AdminMeResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await adminFetch<AdminMeResponse>("/api/v1/admin/me");
      if (cancelled) return;
      if (!result.ok) {
        if (result.status === 401) {
          router.replace("/login");
          return;
        }
        setLoadError(result.title);
        return;
      }
      setStaff(result.data);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onLogout() {
    await adminFetch("/api/v1/admin/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        跳到主内容
      </a>
      <header className={styles.top}>
        <Link className={styles.brand} href="/">
          <span className={styles.mark} aria-hidden="true">
            管
          </span>
          <span>
            <strong>FateRadar</strong>
            <small>运营台</small>
          </span>
        </Link>
        <div className={styles.topMeta}>
          <EnvBadge />
          <span className={styles.staff}>
            {staff ? `${staff.display_name} · ${staff.role}` : "校验会话中…"}
          </span>
          <button className={`${ui.button} ${ui.secondary}`} type="button" onClick={onLogout}>
            退出
          </button>
        </div>
      </header>
      <div className={styles.body}>
        <nav className={styles.nav} aria-label="运营导航">
          {NAV.map((item) => {
            const current =
              item.href === "/"
                ? pathname === "/"
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={current ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <main id="main" className={styles.main}>
          <header className={styles.pageHead}>
            <h1>{title}</h1>
            <p>{duty}</p>
          </header>
          {loadError ? <p className={ui.alert} role="alert">{loadError}</p> : null}
          {children}
        </main>
      </div>
    </div>
  );
}
