"use client";

import { useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminAuditEvent, AdminAuditResponse } from "@/lib/admin-audit";

import styles from "./admin-audit-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "action", header: "动作", sortable: true },
  { key: "actor", header: "操作人", sortable: true },
  { key: "object", header: "对象", sortable: true },
  { key: "result", header: "结果" },
  { key: "createdAt", header: "发生时间", sortable: true },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function objectSummary(event: AdminAuditEvent): string {
  const metadata = event.metadata;
  for (const key of ["target_id", "run_id", "notification_id", "entitlement_id", "family_id"]) {
    const value = metadata[key];
    if (typeof value === "string" && value) return value;
  }
  return "未指定对象";
}

function resultSummary(event: AdminAuditEvent): string {
  const status = event.metadata.status;
  if (typeof status === "string" && status) return status;
  if (event.action.endsWith("retry")) return "已记录重试";
  return "已记录";
}

function rowsFor(events: readonly AdminAuditEvent[]): TableRow[] {
  return events.map((event) => ({
    id: event.id,
    action: event.action,
    actor: event.actor,
    object: objectSummary(event),
    result: resultSummary(event),
    createdAt: formatDate(event.created_at),
  }));
}

export function AdminAuditSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminAuditResponse>({ events: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminAuditResponse>("/api/v1/admin/audit");
      if (cancelled) return;
      if (!response.ok) {
        setState(
          response.status === 403
            ? "forbidden"
            : response.status === 0 || response.status >= 500
              ? "unavailable"
              : "error",
        );
        setError(response.title);
        return;
      }
      setData(response.data);
      setState(response.data.events.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = useMemo(() => rowsFor(data.events), [data.events]);
  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取审计日志…" description="只显示服务端允许展示的审计事实。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="全局员工审计只允许超级管理员查看。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="审计平台暂不可用" description="页面保留只读结构，不显示假审计结果。" />
    ) : state === "error" ? (
      <Status state="error" title="审计日志读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无审计事件" description="管理员成功写入或会话事件产生后，这里会显示可追溯事实。" />
    ) : (
      <Status state="success" title="审计日志已接入" description="元数据按允许键脱敏展示，不包含通知 payload 或其他任意内容。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="audit-list-title">
          <div className={styles.heading}>
            <div>
              <h2 id="audit-list-title">员工审计事件</h2>
              <p>查询动作、操作人、影响对象和结果；详细元数据已由服务端白名单过滤。</p>
            </div>
            <span className={styles.badge}>脱敏读取</span>
          </div>
          <Table
            caption="员工审计事件列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选审计事件"
            filterPlaceholder="例如：动作、操作人或对象…"
            pageSize={20}
            emptyState="当前没有审计事件"
          />
        </section>
      ) : null}
    </div>
  );
}
