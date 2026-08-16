"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";

import styles from "./admin-health-surface.module.css";

type HealthResponse = {
  status: string;
  service: string;
};

export function AdminHealthSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "unavailable" | "error">("loading");
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<HealthResponse>("/api/v1/health/ready");
      if (cancelled) return;
      if (!response.ok) {
        setState(response.status === 0 || response.status >= 500 ? "unavailable" : "error");
        setError(response.title);
        return;
      }
      setData(response.data);
      setState("ready");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在检查依赖…" description="只等待 readiness API 返回真实事实。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="依赖未就绪" description={error ?? "服务依赖暂不可用；没有可核验的正常状态。"} />
    ) : state === "error" ? (
      <Status state="error" title="健康检查失败" description={error ?? "请求失败，请重试。"} />
    ) : (
      <Status state="success" title="依赖已就绪" description="以下内容来自 API readiness 响应，不是页面生成的 KPI。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      <section className={styles.panel} aria-labelledby="health-title">
        <div className={styles.heading}>
          <div>
            <h2 id="health-title">健康检查面</h2>
            <p>当前只接入 API live/ready 的数据库 readiness；Worker、Runtime、支付和通知 SLO 仍需独立接入。</p>
          </div>
          <span className={styles.badge}>真实响应</span>
        </div>
        {state === "ready" && data ? (
          <dl className={styles.details}>
            <div>
              <dt>服务</dt>
              <dd>{data.service}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{data.status}</dd>
            </div>
          </dl>
        ) : (
          <dl className={styles.details}>
            <div>
              <dt>检查来源</dt>
              <dd>readiness API 尚未返回</dd>
            </div>
            <div>
              <dt>当前结论</dt>
              <dd>暂无可核验的实时健康状态</dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
