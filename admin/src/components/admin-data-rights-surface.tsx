"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminClosure, AdminClosuresResponse } from "@/lib/admin-data-rights";

import styles from "./admin-data-rights-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "closure", header: "关闭请求", sortable: true },
  { key: "user", header: "用户", sortable: true },
  { key: "status", header: "状态", sortable: true },
  { key: "requestedAt", header: "请求时间", sortable: true },
  { key: "cancelUntil", header: "可执行时间", sortable: true },
  { key: "action", header: "操作" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusCopy(status: string): string {
  return {
    pending: "待执行",
    executed: "已执行",
    cancelled: "已取消",
  }[status] ?? status;
}

export function AdminDataRightsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const canExecute = effectiveRole === "ops" || effectiveRole === "superadmin";
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminClosuresResponse>({ closures: [] });
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadClosures = useCallback(async () => {
    const response = await adminFetch<AdminClosuresResponse>("/api/v1/admin/privacy/closures");
    if (!response.ok) {
      setState(
        response.status === 403
          ? "forbidden"
          : response.status === 0 || response.status >= 500
            ? "unavailable"
            : "error",
      );
      setError(response.title);
      return false;
    }
    setData(response.data);
    setState(response.data.closures.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminClosuresResponse>("/api/v1/admin/privacy/closures");
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
      setState(response.data.closures.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const execute = useCallback(
    async (item: AdminClosure) => {
      setPendingId(item.closure_id);
      setError(null);
      setResult(null);
      const response = await adminFetch<AdminClosure>(
        `/api/v1/admin/privacy/closures/${item.closure_id}/execute`,
        { method: "POST" },
      );
      if (!response.ok) {
        setError(response.title);
        setPendingId(null);
        return;
      }
      const refreshed = await loadClosures();
      setResult(
        refreshed
          ? "数据权利执行已记录"
          : "数据权利已执行，但列表刷新失败；请重新读取。",
      );
      setPendingId(null);
    },
    [loadClosures],
  );

  const rows = useMemo<TableRow[]>(
    () =>
      data.closures.map((item) => ({
        id: item.closure_id,
        closure: item.closure_id,
        user: item.user_id,
        status: statusCopy(item.status),
        requestedAt: formatDate(item.requested_at),
        cancelUntil: formatDate(item.cancel_until),
        action:
          canExecute && item.status === "pending" ? (
            <Button
              variant="destructive"
              type="button"
              loading={pendingId === item.closure_id}
              aria-label={`执行删除 ${item.closure_id}`}
              onClick={() => void execute(item)}
            >
              执行删除
            </Button>
          ) : (
            "—"
          ),
      })),
    [canExecute, data.closures, execute, pendingId],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取数据权利请求…" description="只显示服务端队列中的关闭事实。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="数据权利关闭队列只允许运营和超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="数据权利平台暂不可用" description="不显示虚假的删除执行结果。" />
    ) : state === "error" ? (
      <Status state="error" title="数据权利读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无待执行请求" description="用户提交数据关闭请求后，这里会显示可执行时间和队列状态。" />
    ) : (
      <Status state="success" title="数据权利队列已接入" description="只执行服务端已确认过等待期的关闭请求，不接受页面自造用户 ID。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {result ? <Status state="success" title={result} description="执行结果来自服务端响应并已刷新队列。" /> : null}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="data-rights-title">
          <div className={styles.heading}>
            <div>
              <h2 id="data-rights-title">数据权利关闭队列</h2>
              <p>查看请求用户、等待期和执行状态；关闭动作不会从页面展示或回传用户私有资料。</p>
            </div>
            <span className={styles.badge}>服务端执行</span>
          </div>
          <Table
            caption="数据权利关闭请求"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选关闭请求"
            filterPlaceholder="例如：请求编号、用户或状态…"
            pageSize={20}
            emptyState="当前没有关闭请求"
          />
        </section>
      ) : null}
    </div>
  );
}
