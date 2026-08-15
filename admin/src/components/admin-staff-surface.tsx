"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminStaff, AdminStaffResponse } from "@/lib/admin-staff";

import styles from "./admin-staff-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "employee", header: "员工", sortable: true },
  { key: "role", header: "角色", sortable: true },
  { key: "sessions", header: "会话", sortable: true },
  { key: "email", header: "邮箱", sortable: true },
  { key: "displayName", header: "显示名称", sortable: true },
  { key: "status", header: "状态", sortable: true },
  { key: "lastLogin", header: "最近登录", sortable: true },
  { key: "action", header: "操作" },
];

const ROLE_OPTIONS: readonly { value: StaffRole; label: string }[] = [
  { value: "support", label: "客服" },
  { value: "finance", label: "财务" },
  { value: "ops", label: "运营" },
  { value: "superadmin", label: "超级管理员" },
];

function roleCopy(role: StaffRole): string {
  return ROLE_OPTIONS.find((item) => item.value === role)?.label ?? role;
}

function statusCopy(status: AdminStaff["status"]): string {
  return status === "active" ? "在职" : "已停用";
}

function formatDate(value: string | null): string {
  if (!value) return "从未登录";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminStaffSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminStaffResponse>({ staff: [] });
  const [roleDraft, setRoleDraft] = useState<Record<string, StaffRole>>({});
  const [reason, setReason] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [createEmail, setCreateEmail] = useState("");
  const [createDisplayName, setCreateDisplayName] = useState("");
  const [createRole, setCreateRole] = useState<StaffRole>("support");
  const [createPassword, setCreatePassword] = useState("");
  const [createReason, setCreateReason] = useState("");
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStaff = useCallback(async () => {
    const response = await adminFetch<AdminStaffResponse>("/api/v1/admin/staff");
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
    setState(response.data.staff.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminStaffResponse>("/api/v1/admin/staff");
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
      setState(response.data.staff.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const update = useCallback(
    async (item: AdminStaff, kind: "status" | "role" | "password") => {
      if (reason.trim().length < 4) {
        setError("请填写至少 4 个字的员工变更原因。");
        return;
      }
      if (kind === "password" && newPassword.length < 8) {
        setError("新密码至少需要 8 个字符。");
        return;
      }
      const key = `${kind}:${item.id}`;
      setPendingKey(key);
      setError(null);
      setResult(null);
      const body =
        kind === "status"
          ? {
              status: item.status === "active" ? "suspended" : "active",
              reason: reason.trim(),
            }
          : kind === "role"
            ? {
              role: roleDraft[item.id] ?? item.role,
              reason: reason.trim(),
            }
            : {
                password: newPassword,
                reason: reason.trim(),
              };
      const endpoint = kind === "password" ? "password-reset" : kind;
      const response = await adminFetch<AdminStaff>(
        `/api/v1/admin/staff/${item.id}/${endpoint}`,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) {
        setError(response.title);
        setPendingKey(null);
        return;
      }
      const refreshed = await loadStaff();
      setResult(
        refreshed
          ? kind === "status"
            ? "员工状态已更新"
            : kind === "role"
              ? "员工角色已更新"
              : "员工密码已重置"
          : "员工变更已保存，但列表刷新失败；请重新读取。",
      );
      if (kind === "password") setNewPassword("");
      setPendingKey(null);
    },
    [loadStaff, newPassword, reason, roleDraft],
  );

  const createStaff = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!createEmail.trim() || !createEmail.includes("@")) {
        setError("请填写有效的员工邮箱。");
        return;
      }
      if (!createDisplayName.trim()) {
        setError("请填写员工显示名称。");
        return;
      }
      if (createPassword.length < 8) {
        setError("新员工初始密码至少需要 8 个字符。");
        return;
      }
      if (createReason.trim().length < 4) {
        setError("请填写至少 4 个字的创建员工原因。");
        return;
      }
      setPendingKey("create");
      setError(null);
      setResult(null);
      const response = await adminFetch<AdminStaff>("/api/v1/admin/staff", {
        method: "POST",
        body: JSON.stringify({
          email: createEmail.trim(),
          display_name: createDisplayName.trim(),
          role: createRole,
          password: createPassword,
          reason: createReason.trim(),
        }),
      });
      if (!response.ok) {
        setError(response.title);
        setPendingKey(null);
        return;
      }
      const refreshed = await loadStaff();
      setResult(
        refreshed
          ? "员工账号已创建"
          : "员工账号已创建，但列表刷新失败；请重新读取。",
      );
      setCreateEmail("");
      setCreateDisplayName("");
      setCreatePassword("");
      setCreateReason("");
      setPendingKey(null);
    },
    [createDisplayName, createEmail, createPassword, createReason, createRole, loadStaff],
  );

  const rows = useMemo<TableRow[]>(
    () =>
      data.staff.map((item) => ({
        id: item.id,
        employee: `${item.display_name} · ${item.email}`,
        email: item.email,
        displayName: item.display_name,
        role: roleCopy(item.role),
        status: statusCopy(item.status),
        lastLogin: formatDate(item.last_login_at),
        sessions: item.unrevoked_session_count,
        action:
          effectiveRole === "superadmin" ? (
            <div className={styles.actionStack}>
              <Button
                variant="destructive"
                type="button"
                loading={pendingKey === `status:${item.id}`}
                aria-label={`${item.status === "active" ? "停用" : "恢复"} ${item.email}`}
                onClick={() => void update(item, "status")}
              >
                {item.status === "active" ? "停用员工" : "恢复员工"}
              </Button>
              <label className={styles.roleField}>
                <span className={styles.srOnly}>角色 {item.email}</span>
                <select
                  aria-label={`角色 ${item.email}`}
                  value={roleDraft[item.id] ?? item.role}
                  onChange={(event) =>
                    setRoleDraft((current) => ({
                      ...current,
                      [item.id]: event.target.value as StaffRole,
                    }))
                  }
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <Button
                variant="secondary"
                type="button"
                loading={pendingKey === `role:${item.id}`}
                aria-label={`保存角色 ${item.email}`}
                onClick={() => void update(item, "role")}
              >
                保存角色
              </Button>
              <Button
                variant="secondary"
                type="button"
                loading={pendingKey === `password:${item.id}`}
                aria-label={`重置密码 ${item.email}`}
                onClick={() => void update(item, "password")}
              >
                重置密码
              </Button>
            </div>
          ) : (
            "—"
          ),
      })),
    [data.staff, effectiveRole, pendingKey, roleDraft, update],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取员工目录…" description="只显示角色、状态和会话计数，不展示密码材料。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="员工目录与角色管理只允许超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="员工平台暂不可用" description="页面保留只读结构，不显示虚假的员工状态。" />
    ) : state === "error" ? (
      <Status state="error" title="员工目录读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无员工账号" description="员工账号创建后，这里会显示可审计的角色和状态。" />
    ) : (
      <Status state="success" title="员工目录已接入" description="密码哈希、会话 token 和其他秘密材料不进入 Admin 响应。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {result ? <Status state="success" title={result} description="变更已通过服务端角色、CSRF 和审计校验。" /> : null}
      {state !== "forbidden" ? <section className={styles.panel} aria-labelledby="staff-list-title">
        <div className={styles.heading}>
          <div>
            <h2 id="staff-list-title">员工与角色</h2>
            <p>查看员工、角色、状态和未撤销会话；状态/角色变更会立即撤销既有会话。</p>
          </div>
          <span className={styles.badge}>无密码材料</span>
        </div>
        <Table
          caption="员工目录"
          columns={COLUMNS}
          rows={rows}
          filterLabel="筛选员工目录"
          filterPlaceholder="例如：邮箱、角色或状态…"
          pageSize={20}
          emptyState={state === "unavailable" ? "服务端员工事实暂不可用" : "当前没有员工账号"}
        />
      </section> : null}
      {effectiveRole === "superadmin" && state !== "forbidden" ? (
        <section className={styles.panel} aria-labelledby="staff-command-title">
          <div className={styles.heading}>
            <div>
              <h2 id="staff-command-title">员工变更原因</h2>
              <p>停用、恢复和角色调整必须填写原因；密码只用于服务端哈希，不会进入响应或审计。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <label className={styles.reasonField} htmlFor="staff-change-reason">
            员工变更原因
            <textarea
              id="staff-change-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              minLength={4}
              placeholder="说明离岗、职责调整或恢复值班原因…"
            />
          </label>
          <label className={styles.passwordField} htmlFor="staff-new-password">
            新密码
            <input
              id="staff-new-password"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              minLength={8}
              maxLength={200}
              autoComplete="new-password"
              placeholder="至少 8 个字符；不会回显到列表或审计"
            />
          </label>
          {error ? <p className={styles.inlineAlert} role="alert">{error}</p> : null}
        </section>
      ) : null}
      {effectiveRole === "superadmin" && state !== "forbidden" ? (
        <section className={styles.panel} aria-labelledby="staff-create-title">
          <div className={styles.heading}>
            <div>
              <h2 id="staff-create-title">创建员工账号</h2>
              <p>创建本地员工登录账号；当前流程不发送邮件邀请，初始密码仅在提交时使用。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <form className={styles.createForm} onSubmit={(event) => void createStaff(event)}>
            <div className={styles.fieldGrid}>
              <label className={styles.inputField} htmlFor="new-staff-email">
                新员工邮箱
                <input
                  id="new-staff-email"
                  type="email"
                  value={createEmail}
                  onChange={(event) => setCreateEmail(event.target.value)}
                  autoComplete="off"
                  required
                  placeholder="例如：operator@example.com"
                />
              </label>
              <label className={styles.inputField} htmlFor="new-staff-display-name">
                新员工显示名称
                <input
                  id="new-staff-display-name"
                  type="text"
                  value={createDisplayName}
                  onChange={(event) => setCreateDisplayName(event.target.value)}
                  maxLength={120}
                  required
                  placeholder="例如：运营值班"
                />
              </label>
            </div>
            <label className={styles.inputField} htmlFor="new-staff-role">
              新员工角色
              <select
                id="new-staff-role"
                aria-label="新员工角色"
                value={createRole}
                onChange={(event) => setCreateRole(event.target.value as StaffRole)}
              >
                {ROLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.passwordField} htmlFor="new-staff-password">
              新员工初始密码
              <input
                id="new-staff-password"
                type="password"
                value={createPassword}
                onChange={(event) => setCreatePassword(event.target.value)}
                minLength={8}
                maxLength={200}
                autoComplete="new-password"
                required
                placeholder="至少 8 个字符；创建后不会再次显示"
              />
            </label>
            <label className={styles.reasonField} htmlFor="new-staff-reason">
              创建员工原因
              <textarea
                id="new-staff-reason"
                value={createReason}
                onChange={(event) => setCreateReason(event.target.value)}
                minLength={4}
                required
                placeholder="说明新增账号的岗位和排班原因…"
              />
            </label>
            <Button type="submit" loading={pendingKey === "create"}>
              创建员工账号
            </Button>
          </form>
        </section>
      ) : null}
    </div>
  );
}
