"use client";

import { useEffect, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { KpiChip } from "@/components/kpi-chip";
import { StatusTag } from "@/components/status-tag";
import { Status } from "@/components/ui";
import { adminFetch, type AdminOverviewResponse } from "@/lib/api";

import styles from "./admin-overview-page.module.css";

type OverviewState =
  | { kind: "loading" }
  | { kind: "error"; status: number; title: string }
  | { kind: "stub" }
  | { kind: "ready"; data: AdminOverviewResponse };

export function AdminOverviewPage() {
  const [overview, setOverview] = useState<OverviewState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await adminFetch<AdminOverviewResponse>("/api/v1/admin/overview");
      if (cancelled) return;
      if (!result.ok) {
        setOverview({ kind: "error", status: result.status, title: result.title });
        return;
      }
      setOverview(result.data.is_stub ? { kind: "stub" } : { kind: "ready", data: result.data });
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AdminShell title="总览" duty="看待办、看异常，不讲故事；只有真实聚合数据才显示数字。">
      {overview.kind === "loading" ? (
        <Status state="loading" title="正在读取总览…" description="正在读取真实平台聚合。" />
      ) : overview.kind === "stub" ? (
        <Status
          state="unavailable"
          title="总览数据待接入"
          description="后端当前返回占位合同；页面不会把 0 当作待办、订单或告警事实。"
        />
      ) : overview.kind === "error" ? (
        <Status
          state={overview.status === 401 ? "unauthorized" : "error"}
          title={overview.status === 401 ? "需要登录" : "总览读取失败"}
          description={overview.title}
        />
      ) : (
        <div className={styles.stack}>
          <section aria-labelledby="overview-kpis-title">
            <h2 className="sr-only" id="overview-kpis-title">业务关键指标</h2>
            <div className={styles.kpiGrid}>
              {overview.data.kpis.map((kpi) => (
                <KpiChip
                  key={kpi.id}
                  label={kpi.label}
                  value={kpi.value}
                  isStub={false}
                />
              ))}
            </div>
          </section>
          <section className={styles.queueSection} aria-labelledby="overview-queues-title">
            <div className={styles.sectionHeading}>
              <h2 id="overview-queues-title">工作队列</h2>
              <StatusTag tone="pending">实时聚合</StatusTag>
            </div>
            {overview.data.queues.length === 0 ? (
              <p className={styles.empty}>当前没有待处理队列。</p>
            ) : (
              <ul className={styles.queueList}>
                {overview.data.queues.map((queue) => (
                  <li key={queue.id}>
                    <span>{queue.label}</span>
                    <strong>{queue.count}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </AdminShell>
  );
}
