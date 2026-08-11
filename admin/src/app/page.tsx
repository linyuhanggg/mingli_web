"use client";

import { useEffect, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { KpiChip } from "@/components/kpi-chip";
import { StatusTag } from "@/components/status-tag";
import ui from "@/components/ui.module.css";
import { adminFetch, type AdminOverviewResponse } from "@/lib/api";

const FALLBACK: AdminOverviewResponse = {
  generated_at: new Date(0).toISOString(),
  is_stub: true,
  kpis: [
    { id: "refunds_pending", label: "待审退款", value: 0, is_stub: true },
    { id: "readings_failed", label: "失败解读", value: 0, is_stub: true },
    { id: "payments_abnormal", label: "今日支付异常", value: 0, is_stub: true },
    { id: "reconcile_diff", label: "对账差异", value: 0, is_stub: true },
  ],
  queues: [
    { id: "refund_queue", label: "退款审批队列", count: 0, is_stub: true },
    { id: "reading_queue", label: "解读失败队列", count: 0, is_stub: true },
  ],
};

export default function OverviewPage() {
  const [data, setData] = useState<AdminOverviewResponse>(FALLBACK);
  const [note, setNote] = useState<string | null>("正在读取总览…");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await adminFetch<AdminOverviewResponse>("/api/v1/admin/overview");
      if (cancelled) return;
      if (!result.ok) {
        setNote(result.status === 401 ? "需要登录" : `总览暂不可用：${result.title}`);
        return;
      }
      setData(result.data);
      setNote(result.data.is_stub ? "当前 KPI 为占位，领域计数尚未接入。" : null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AdminShell title="总览" duty="看待办、看异常，不讲故事。数字未接入前会标明待接入。">
      {note ? <p className={ui.muted}>{note}</p> : null}
      <div className={ui.kpiGrid}>
        {data.kpis.map((kpi) => (
          <KpiChip
            key={kpi.id}
            label={kpi.label}
            value={kpi.value}
            isStub={kpi.is_stub}
          />
        ))}
      </div>
      <section className={`${ui.paper} ${ui.stack}`}>
        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontFamily: "var(--font-serif)", fontSize: "1.2rem" }}>
            工作队列
          </h2>
          <StatusTag tone="pending">处理中</StatusTag>
        </div>
        {data.queues.length === 0 ? (
          <p className={ui.empty}>暂无队列。</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {data.queues.map((queue) => (
              <li key={queue.id}>
                {queue.label}：{queue.count}
                {queue.is_stub ? "（待接入）" : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
    </AdminShell>
  );
}
