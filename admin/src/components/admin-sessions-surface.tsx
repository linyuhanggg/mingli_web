"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import {
  Button,
  Dialog,
  DialogFooter,
  Field,
  Status,
  Table,
  type TableColumn,
  type TableRow,
} from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminSession, AdminSessionsResponse } from "@/lib/admin-sessions";

import styles from "./admin-sessions-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "actor", header: "员工", sortable: true },
  { key: "status", header: "状态", sortable: true },
  { key: "lastSeenAt", header: "最近活动", sortable: true },
  { key: "expiresAt", header: "到期时间", sortable: true },
  { key: "action", header: "操作" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusCopy(status: AdminSession["status"]): string {
  return {
    active: "有效",
    expired: "已过期",
    revoked: "已撤销",
  }[status];
}

export function AdminSessionsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminSessionsResponse>({ sessions: [] });
  const [reason, setReason] = useState("");
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    const response = await adminFetch<AdminSessionsResponse>("/api/v1/admin/sessions");
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
    setState(response.data.sessions.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminSessionsResponse>("/api/v1/admin/sessions");
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
      setState(response.data.sessions.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const revoke = useCallback(
    async (item: AdminSession) => {
      if (reason.trim().length < 4) {
        setError("请填写至少 4 个字的会话强退原因。");
        return;
      }
      setPendingId(item.id);
      setError(null);
      setResult(null);
      const response = await adminFetch<AdminSession>(
        `/api/v1/admin/sessions/${item.id}/revoke`,
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
      setResult("会话已撤销并记录审计；关闭确认层后会刷新列表。");
      setPendingId(null);
    },
    [reason],
  );

  const changeRevokeDialog = useCallback(
    (open: boolean, item: AdminSession) => {
      if (open) {
        setSelectedSessionId(item.id);
        setReason("");
        setResult(null);
        setError(null);
        return;
      }
      setSelectedSessionId(null);
      setReason("");
      setError(null);
      if (result) void loadSessions();
      setResult(null);
    },
    [loadSessions, result],
  );

  const rows = useMemo<TableRow[]>(
    () =>
      data.sessions.map((item) => ({
        id: item.id,
        actor: item.actor,
        status: statusCopy(item.status),
        lastSeenAt: formatDate(item.last_seen_at),
        expiresAt: formatDate(item.expires_at),
        action:
          effectiveRole === "superadmin" && item.status === "active" ? (
            <Dialog
              open={selectedSessionId === item.id}
              onOpenChange={(open) => changeRevokeDialog(open, item)}
              title={`撤销会话 · ${item.actor}`}
              description="强退会立即使该员工的当前会话失效，且每次操作都会留下审计记录。"
              trigger={<Button variant="destructive">撤销会话</Button>}
            >
              <dl className={styles.impactSummary}>
                <div>
                  <dt>影响对象</dt>
                  <dd>{item.actor}</dd>
                </div>
                <div>
                  <dt>会话编号</dt>
                  <dd>{item.id}</dd>
                </div>
                <div>
                  <dt>审计结果</dt>
                  <dd>记录强退原因、操作员工与目标会话</dd>
                </div>
              </dl>
              <Field
                label="会话强退原因"
                description="至少 4 个字，例如异常登录、人员离职或权限回收。"
                required
              >
                <input
                  type="text"
                  name="session-revoke-reason"
                  autoComplete="off"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  minLength={4}
                />
              </Field>
              {error ? <Status state="error" title="会话强退失败" description={error} /> : null}
              {result ? <Status state="success" title="会话已撤销" description={result} /> : null}
              <DialogFooter>
                <Button variant="ghost" type="button" onClick={() => changeRevokeDialog(false, item)}>
                  取消
                </Button>
                <Button
                  type="button"
                  loading={pendingId === item.id}
                  disabled={reason.trim().length < 4 || Boolean(result)}
                  aria-describedby={`session-revoke-help-${item.id}`}
                  onClick={() => void revoke(item)}
                >
                  确认并记录审计
                </Button>
              </DialogFooter>
              <p className={styles.submitHelp} id={`session-revoke-help-${item.id}`}>
                {result ? "操作已完成，可关闭确认层。" : "填写至少 4 个字的原因后可确认。"}
              </p>
            </Dialog>
          ) : (
            "—"
          ),
      })),
    [changeRevokeDialog, data.sessions, effectiveRole, error, pendingId, reason, result, revoke, selectedSessionId],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取员工会话…" description="只显示会话元数据，不展示 opaque token 材料。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="员工会话查看与强退只允许超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="会话平台暂不可用" description="页面保留只读结构，不显示虚假的会话状态。" />
    ) : state === "error" ? (
      <Status state="error" title="员工会话读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无员工会话" description="员工登录后，这里会显示可撤销的会话元数据。" />
    ) : (
      <Status state="success" title="员工会话已接入" description="列表只展示会话元数据，不包含会话密钥或防伪校验材料。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="sessions-list-title">
          <div className={styles.heading}>
            <div>
              <h2 id="sessions-list-title">员工会话</h2>
              <p>按员工、活动时间和到期时间查看会话；服务端负责最终角色校验。</p>
            </div>
            <span className={styles.badge}>无秘密字段</span>
          </div>
          <Table
            caption="员工会话列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选员工会话"
            filterPlaceholder="例如：员工邮箱、状态或时间…"
            pageSize={20}
            emptyState="当前没有员工会话"
          />
        </section>
      ) : null}
    </div>
  );
}
