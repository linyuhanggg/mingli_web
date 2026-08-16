"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminSupportCase,
  AdminSupportCaseCategory,
  AdminSupportCasesResponse,
} from "@/lib/admin-support-cases";

import styles from "./admin-entitlements-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "case", header: "案件", sortable: true },
  { key: "subject", header: "对象", sortable: true },
  { key: "category", header: "类型", sortable: true },
  { key: "summary", header: "摘要" },
  { key: "status", header: "状态", sortable: true },
  { key: "createdAt", header: "提交时间", sortable: true },
];

type SurfaceState = "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function categoryCopy(value: AdminSupportCaseCategory): string {
  return {
    account: "账户",
    delivery: "交付",
    billing: "账务",
    reading: "解读",
    referral: "邀请",
    profile_correction: "资料纠正",
    algorithm_review: "算法复核",
    after_sales: "售后",
    compensation: "补偿",
    other: "其他",
  }[value];
}

function statusCopy(value: AdminSupportCase["status"]): string {
  return {
    open: "待处理",
    in_review: "处理中",
    resolved: "已解决",
    rejected: "已驳回",
  }[value];
}

export function AdminSupportCasesSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const canSubmit = effectiveRole === "support" || effectiveRole === "superadmin";
  const [state, setState] = useState<SurfaceState>("loading");
  const [data, setData] = useState<AdminSupportCasesResponse>({ cases: [] });
  const [subjectRef, setSubjectRef] = useState("");
  const [ownerUserId, setOwnerUserId] = useState("");
  const [category, setCategory] = useState<AdminSupportCaseCategory>("account");
  const [summary, setSummary] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadCases = useCallback(async () => {
    const response = await adminFetch<AdminSupportCasesResponse>(
      "/api/v1/admin/support-cases",
    );
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
    setState(response.data.cases.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminSupportCasesResponse>(
        "/api/v1/admin/support-cases",
      );
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
      setState(response.data.cases.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    const response = await adminFetch<AdminSupportCase>(
      "/api/v1/admin/support-cases",
      {
        method: "POST",
        body: JSON.stringify({
          owner_user_id: ownerUserId.trim() || null,
          subject_ref: subjectRef.trim(),
          category,
          summary: summary.trim(),
          reason: reason.trim(),
        }),
      },
    );
    if (!response.ok) {
      setError(response.title);
      setSubmitting(false);
      return;
    }
    setResult("客服案件已提交");
    setSubjectRef("");
    setOwnerUserId("");
    setSummary("");
    setReason("");
    await loadCases();
    setSubmitting(false);
  }

  const rows = useMemo<TableRow[]>(
    () =>
      data.cases.map((item) => ({
        id: item.id,
        case: item.id,
        subject: item.subject_ref,
        category: categoryCopy(item.category),
        summary: item.summary,
        status: statusCopy(item.status),
        createdAt: formatDate(item.created_at),
      })),
    [data.cases],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取客服案件…" description="只显示服务端已保存的案件申请，不执行补偿或修改业务对象。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="当前员工角色不能读取客服案件。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="客服案件平台暂不可用" description="页面保留结构，不显示虚假的案件或处理结果。" />
    ) : state === "error" ? (
      <Status state="error" title="客服案件读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无客服案件" description="客服提交申请后，这里会显示服务端保存的对象、类型和状态。" />
    ) : (
      <Status state="success" title="客服案件已接入" description="页面只提交案件申请；补偿、退款和状态处理仍由各自受控服务负责。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {result ? <Status state="success" title={result} description="案件已通过服务端角色、CSRF 和审计校验，并重新读取列表。" /> : null}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="support-cases-title">
          <div className={styles.heading}>
            <div>
              <h2 id="support-cases-title">客服案件</h2>
              <p>记录需要运营后续处理的请求；案件申请不会直接授予权益、退款或改变报告状态。</p>
            </div>
            <span className={styles.badge}>申请队列</span>
          </div>
          <Table
            caption="客服案件列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选客服案件"
            filterPlaceholder="例如：案件、对象、类型或状态…"
            pageSize={20}
            emptyState="当前没有客服案件"
          />
          {canSubmit ? (
            <form className={styles.form} onSubmit={(event) => void submit(event)}>
              <label className={styles.field}>
                <span>对象编号</span>
                <input value={subjectRef} onChange={(event) => setSubjectRef(event.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>用户 ID（可选）</span>
                <input value={ownerUserId} onChange={(event) => setOwnerUserId(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>案件类型</span>
                <select value={category} onChange={(event) => setCategory(event.target.value as AdminSupportCaseCategory)}>
                  <option value="account">账户</option>
                  <option value="delivery">交付</option>
                  <option value="billing">账务</option>
                  <option value="reading">解读</option>
                  <option value="referral">邀请</option>
                  <option value="profile_correction">资料纠正</option>
                  <option value="algorithm_review">算法复核</option>
                  <option value="after_sales">售后</option>
                  <option value="compensation">补偿</option>
                  <option value="other">其他</option>
                </select>
              </label>
              <label className={`${styles.field} ${styles.wide}`}>
                <span>案件摘要</span>
                <input value={summary} onChange={(event) => setSummary(event.target.value)} required />
              </label>
              <label className={`${styles.field} ${styles.wide}`}>
                <span>操作原因</span>
                <input value={reason} onChange={(event) => setReason(event.target.value)} required />
              </label>
              {error ? <p className={styles.inlineAlert} role="alert">{error}</p> : null}
              <div className={styles.actions}>
                <Button type="submit" loading={submitting}>提交客服案件</Button>
              </div>
            </form>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
