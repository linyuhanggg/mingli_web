"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Field, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminNotification, AdminNotificationsResponse } from "@/lib/admin-notifications";

import styles from "./admin-notifications-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "kind", header: "通知类型", sortable: true },
  { key: "channel", header: "渠道", sortable: true },
  { key: "status", header: "投递状态", sortable: true },
  { key: "attempts", header: "尝试次数", sortable: true },
  { key: "availableAt", header: "可投递时间", sortable: true },
  { key: "lastError", header: "最近错误" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusCopy(status: AdminNotification["status"]): string {
  return {
    pending: "待投递",
    processing: "投递中",
    sent: "已发送",
    failed: "终态失败",
  }[status];
}

export function AdminNotificationsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminNotificationsResponse>({ notifications: [] });
  const [reason, setReason] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reasonError, setReasonError] = useState<string | undefined>();
  const reasonRef = useRef<HTMLTextAreaElement>(null);

  const loadNotifications = useCallback(async () => {
    const response = await adminFetch<AdminNotificationsResponse>("/api/v1/admin/notifications");
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
    setState(response.data.notifications.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminNotificationsResponse>("/api/v1/admin/notifications");
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
      setState(response.data.notifications.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = useCallback(
    async (item: AdminNotification) => {
      if (reason.trim().length < 4) {
        const message = "请填写至少 4 个字的通知重试原因。";
        setReasonError(message);
        setError(message);
        reasonRef.current?.focus();
        return;
      }
      setReasonError(undefined);
      setPendingId(item.id);
      setError(null);
      setResult(null);
      const response = await adminFetch<AdminNotification>(
        `/api/v1/admin/notifications/${item.id}/retry`,
        {
          method: "POST",
          body: JSON.stringify({ reason: reason.trim() }),
        },
      );
      if (!response.ok) {
        setError(response.title);
        setPendingId(null);
        return;
      }
      const refreshed = await loadNotifications();
      setResult(
        refreshed
          ? "通知已重新排队，尝试次数保持不变。"
          : "通知已重新排队，但列表刷新失败；请重新读取。",
      );
      setPendingId(null);
    },
    [loadNotifications, reason],
  );

  const rows = useMemo<TableRow[]>(
    () =>
      data.notifications.map((item) => ({
        id: item.id,
        kind: item.kind,
        channel: item.channel ?? "未标记",
        status: statusCopy(item.status),
        attempts: item.attempt_count,
        availableAt: formatDate(item.available_at),
        lastError: item.last_error ?? "—",
      })),
    [data.notifications],
  );
  const selectedNotification = useMemo(
    () =>
      data.notifications.find((item) => item.id === selectedId) ??
      data.notifications.find((item) => item.status === "failed") ??
      data.notifications[0] ??
      null,
    [data.notifications, selectedId],
  );

  const notice = result ? (
    <Status compact state="success" title={result} description="重试命令已通过服务端 CSRF、角色和审计校验。" />
  ) : state === "loading" ? (
      <Status compact state="loading" title="正在读取通知投递…" description="只显示服务端 Outbox 状态，不展示通知 payload。" />
    ) : state === "forbidden" ? (
      <Status compact state="locked" title="无权限" description="通知投递管理只允许超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status compact state="unavailable" title="通知平台暂不可用" description="页面保留只读结构，不显示虚假的投递结果。" />
    ) : state === "error" ? (
      <Status compact state="error" title="通知读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status compact state="empty" title="暂无通知投递记录" description="用户偏好允许且服务端入队后，这里会显示 Outbox 事实。" />
    ) : null;

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" ? <section className={styles.panel} aria-labelledby="notifications-list-title">
        <div className={styles.heading}>
          <div>
            <h2 id="notifications-list-title">通知投递状态</h2>
            <p>按 Outbox 状态查看站内、邮件和短信的投递事实；内容 payload 不进入 Admin。</p>
          </div>
          <span className={styles.badge}>无 payload</span>
        </div>
        <Table
          caption="通知投递列表"
          columns={COLUMNS}
          rows={rows}
          filterLabel="筛选通知投递"
          filterPlaceholder="例如：通知类型、渠道或状态…"
          filter={{
            label: "按投递状态筛选",
            rowKey: "status",
            options: [
              { value: "", label: "全部" },
              { value: "待投递", label: "待投递" },
              { value: "投递中", label: "投递中" },
              { value: "已发送", label: "已发送" },
              { value: "终态失败", label: "失败" },
            ],
          }}
          pageSize={10}
          emptyState="没有符合筛选条件的通知投递记录"
          onRowActivate={(row) => setSelectedId(row.id)}
          rowActionLabel="处理"
        />
      </section> : null}
      {effectiveRole === "superadmin" && state === "ready" ? (
        <section className={styles.panel} aria-labelledby="notifications-command-title">
          <div className={styles.heading}>
            <div>
              <h2 id="notifications-command-title">重新投递失败通知</h2>
              <p>只能重排终态 `failed` 记录；保留原尝试次数，不清除最近错误。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <Field
            className={styles.workbenchField}
            label="操作原因"
            description="至少 4 个字；原因会随本次重试写入审计。"
            error={reasonError}
            required
          >
            <textarea
              ref={reasonRef}
              id="notification-retry-reason"
              name="notificationRetryReason"
              autoComplete="off"
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                if (event.target.value.trim().length >= 4) setReasonError(undefined);
              }}
              minLength={4}
              placeholder="说明供应商恢复、人工确认等重试原因…"
            />
          </Field>
          {selectedNotification ? (
            <p aria-live="polite">当前处理通知：{selectedNotification.id}</p>
          ) : null}
          {selectedNotification?.status === "failed" ? (
            <Button
              variant="secondary"
              type="button"
              loading={pendingId === selectedNotification.id}
              onClick={() => void retry(selectedNotification)}
            >
              重新投递
            </Button>
          ) : selectedNotification ? (
            <p>当前选中的通知不是终态失败记录，无需重新投递。</p>
          ) : null}
          {error ? <p className={styles.inlineAlert} role="alert">{error}</p> : null}
        </section>
      ) : null}
    </div>
  );
}
