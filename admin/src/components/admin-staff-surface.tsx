"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Field, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
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
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
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
  const [reasonError, setReasonError] = useState<string | undefined>();
  const [passwordError, setPasswordError] = useState<string | undefined>();
  const [createErrors, setCreateErrors] = useState<{
    email?: string;
    displayName?: string;
    password?: string;
    reason?: string;
  }>({});
  const [createSummary, setCreateSummary] = useState<string | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const createEmailRef = useRef<HTMLInputElement>(null);
  const createDisplayNameRef = useRef<HTMLInputElement>(null);
  const createPasswordRef = useRef<HTMLInputElement>(null);
  const createReasonRef = useRef<HTMLTextAreaElement>(null);

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
        const message = "请填写至少 4 个字的员工变更原因。";
        setReasonError(message);
        setError(message);
        reasonRef.current?.focus();
        return;
      }
      if (kind === "password" && newPassword.length < 8) {
        const message = "新密码至少需要 8 个字符。";
        setPasswordError(message);
        setError(message);
        passwordRef.current?.focus();
        return;
      }
      setReasonError(undefined);
      setPasswordError(undefined);
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
        const message = "请填写有效的员工邮箱。";
        setCreateErrors({ email: message });
        setCreateSummary(message);
        createEmailRef.current?.focus();
        return;
      }
      if (!createDisplayName.trim()) {
        const message = "请填写员工显示名称。";
        setCreateErrors({ displayName: message });
        setCreateSummary(message);
        createDisplayNameRef.current?.focus();
        return;
      }
      if (createPassword.length < 8) {
        const message = "新员工初始密码至少需要 8 个字符。";
        setCreateErrors({ password: message });
        setCreateSummary(message);
        createPasswordRef.current?.focus();
        return;
      }
      if (createReason.trim().length < 4) {
        const message = "请填写至少 4 个字的创建员工原因。";
        setCreateErrors({ reason: message });
        setCreateSummary(message);
        createReasonRef.current?.focus();
        return;
      }
      setCreateErrors({});
      setCreateSummary(null);
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
        setCreateSummary(response.title);
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
      })),
    [data.staff],
  );
  const selectedStaff = useMemo(
    () => data.staff.find((item) => item.id === selectedStaffId) ?? data.staff[0] ?? null,
    [data.staff, selectedStaffId],
  );

  const notice = result ? (
    <Status compact state="success" title={result} description="变更已通过服务端角色、CSRF 和审计校验。" />
  ) : state === "loading" ? (
      <Status compact state="loading" title="正在读取员工目录…" description="只显示角色、状态和会话计数，不展示密码材料。" />
    ) : state === "forbidden" ? (
      <Status compact state="locked" title="无权限" description="员工目录与角色管理只允许超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status compact state="unavailable" title="员工平台暂不可用" description="页面保留只读结构，不显示虚假的员工状态。" />
    ) : state === "error" ? (
      <Status compact state="error" title="员工目录读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status compact state="empty" title="暂无员工账号" description="员工账号创建后，这里会显示可审计的角色和状态。" />
    ) : null;

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" ? <section className={styles.panel} aria-labelledby="staff-list-title">
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
          filter={{
            label: "按员工状态筛选",
            rowKey: "status",
            options: [
              { value: "", label: "全部" },
              { value: "在职", label: "在职员工" },
              { value: "已停用", label: "停用员工" },
            ],
          }}
          pageSize={20}
          emptyState="没有符合筛选条件的员工账号"
          onRowActivate={(row) => setSelectedStaffId(row.id)}
          rowActionLabel="处理"
        />
      </section> : null}
      {effectiveRole === "superadmin" && state === "ready" ? (
        <section className={styles.panel} aria-labelledby="staff-command-title">
          <div className={styles.heading}>
            <div>
              <h2 id="staff-command-title">处理所选员工</h2>
              <p>停用、恢复和角色调整必须填写原因；密码只用于服务端哈希，不会进入响应或审计。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <Field
            className={styles.workbenchField}
            label="员工变更原因"
            description="至少 4 个字；原因会随停用、恢复、角色或密码操作写入审计。"
            error={reasonError}
            required
          >
            <textarea
              ref={reasonRef}
              id="staff-change-reason"
              name="staffChangeReason"
              autoComplete="off"
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                if (event.target.value.trim().length >= 4) setReasonError(undefined);
              }}
              minLength={4}
              placeholder="说明离岗、职责调整或恢复值班原因…"
            />
          </Field>
          <Field
            className={styles.workbenchField}
            label="新密码"
            description="仅重置密码时填写，至少 8 个字符；不会回显到列表或审计。"
            error={passwordError}
          >
            <input
              ref={passwordRef}
              id="staff-new-password"
              name="staffNewPassword"
              type="password"
              value={newPassword}
              onChange={(event) => {
                setNewPassword(event.target.value);
                if (event.target.value.length >= 8) setPasswordError(undefined);
              }}
              minLength={8}
              maxLength={200}
              autoComplete="new-password"
              placeholder="至少 8 个字符；不会回显到列表或审计"
            />
          </Field>
          {selectedStaff ? (
            <p aria-live="polite">当前处理员工：{selectedStaff.display_name} · {selectedStaff.email}</p>
          ) : null}
          {selectedStaff ? (
            <div className={styles.actionStack}>
              <Button
                variant="destructive"
                type="button"
                loading={pendingKey === `status:${selectedStaff.id}`}
                aria-label={`${selectedStaff.status === "active" ? "停用" : "恢复"} ${selectedStaff.email}`}
                onClick={() => void update(selectedStaff, "status")}
              >
                {selectedStaff.status === "active" ? "停用员工" : "恢复员工"}
              </Button>
              <Field className={styles.workbenchField} label={`目标角色 · ${selectedStaff.email}`}>
                <select
                  aria-label={`角色 ${selectedStaff.email}`}
                  name="staffTargetRole"
                  autoComplete="off"
                  value={roleDraft[selectedStaff.id] ?? selectedStaff.role}
                  onChange={(event) =>
                    setRoleDraft((current) => ({
                      ...current,
                      [selectedStaff.id]: event.target.value as StaffRole,
                    }))
                  }
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Button
                variant="secondary"
                type="button"
                loading={pendingKey === `role:${selectedStaff.id}`}
                aria-label={`保存角色 ${selectedStaff.email}`}
                onClick={() => void update(selectedStaff, "role")}
              >
                保存角色
              </Button>
              <Button
                variant="secondary"
                type="button"
                loading={pendingKey === `password:${selectedStaff.id}`}
                aria-label={`重置密码 ${selectedStaff.email}`}
                onClick={() => void update(selectedStaff, "password")}
              >
                重置密码
              </Button>
            </div>
          ) : null}
          {error ? <p className={styles.inlineAlert} role="alert">{error}</p> : null}
        </section>
      ) : null}
      {effectiveRole === "superadmin" && state === "ready" ? (
        <section className={styles.panel} aria-labelledby="staff-create-title">
          <div className={styles.heading}>
            <div>
              <h2 id="staff-create-title">创建员工账号</h2>
              <p>创建本地员工登录账号；当前流程不发送邮件邀请，初始密码仅在提交时使用。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <form className={styles.createForm} noValidate onSubmit={(event) => void createStaff(event)}>
            <div className={styles.fieldGrid}>
              <Field className={styles.workbenchField} label="新员工邮箱" error={createErrors.email} required>
                <input
                  ref={createEmailRef}
                  id="new-staff-email"
                  name="newStaffEmail"
                  type="email"
                  value={createEmail}
                  onChange={(event) => {
                    setCreateEmail(event.target.value);
                    if (event.target.value.includes("@")) {
                      setCreateErrors((current) => ({ ...current, email: undefined }));
                      setCreateSummary(null);
                    }
                  }}
                  autoComplete="off"
                  spellCheck={false}
                  required
                  placeholder="例如：operator@example.com"
                />
              </Field>
              <Field className={styles.workbenchField} label="新员工显示名称" error={createErrors.displayName} required>
                <input
                  ref={createDisplayNameRef}
                  id="new-staff-display-name"
                  name="newStaffDisplayName"
                  type="text"
                  value={createDisplayName}
                  onChange={(event) => {
                    setCreateDisplayName(event.target.value);
                    if (event.target.value.trim()) {
                      setCreateErrors((current) => ({ ...current, displayName: undefined }));
                      setCreateSummary(null);
                    }
                  }}
                  maxLength={120}
                  autoComplete="off"
                  required
                  placeholder="例如：运营值班"
                />
              </Field>
            </div>
            <Field className={styles.workbenchField} label="新员工角色">
              <select
                id="new-staff-role"
                name="newStaffRole"
                autoComplete="off"
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
            </Field>
            <Field
              className={styles.workbenchField}
              label="新员工初始密码"
              description="至少 8 个字符；创建后不会再次显示。"
              error={createErrors.password}
              required
            >
              <input
                ref={createPasswordRef}
                id="new-staff-password"
                name="newStaffPassword"
                type="password"
                value={createPassword}
                onChange={(event) => {
                  setCreatePassword(event.target.value);
                  if (event.target.value.length >= 8) {
                    setCreateErrors((current) => ({ ...current, password: undefined }));
                    setCreateSummary(null);
                  }
                }}
                minLength={8}
                maxLength={200}
                autoComplete="new-password"
                required
                placeholder="至少 8 个字符；创建后不会再次显示"
              />
            </Field>
            <Field
              className={styles.workbenchField}
              label="创建员工原因"
              description="至少 4 个字；原因会和创建操作一起写入审计。"
              error={createErrors.reason}
              required
            >
              <textarea
                ref={createReasonRef}
                id="new-staff-reason"
                name="newStaffReason"
                autoComplete="off"
                value={createReason}
                onChange={(event) => {
                  setCreateReason(event.target.value);
                  if (event.target.value.trim().length >= 4) {
                    setCreateErrors((current) => ({ ...current, reason: undefined }));
                    setCreateSummary(null);
                  }
                }}
                minLength={4}
                required
                placeholder="说明新增账号的岗位和排班原因…"
              />
            </Field>
            {createSummary ? <p className={styles.inlineAlert} role="alert">{createSummary}</p> : null}
            <Button type="submit" loading={pendingKey === "create"}>
              创建员工账号
            </Button>
          </form>
        </section>
      ) : null}
    </div>
  );
}
