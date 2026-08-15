"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Status } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminReferralAppeal,
  AdminReferralAppealsResponse,
  AdminReferralRiskSignal,
} from "@/lib/admin-appeals";

import formStyles from "./admin-entitlements-surface.module.css";
import styles from "./admin-referrals-surface.module.css";

type SurfaceState = "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusCopy(value: AdminReferralAppeal["status"]): string {
  return {
    submitted: "待复核",
    accepted: "申诉已接受",
    rejected: "申诉已驳回",
    correction_pending: "等待第二位审批",
    corrected: "纠错已完成",
  }[value];
}

function signalCopy(signal: AdminReferralRiskSignal): string {
  return `${signal.signal_type} · ${signal.severity}`;
}

export function AdminAppealsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const canSubmit = effectiveRole === "support" || effectiveRole === "superadmin";
  const canDecide = effectiveRole === "finance" || effectiveRole === "superadmin";
  const canRecordRisk = effectiveRole === "ops" || effectiveRole === "superadmin";
  const [state, setState] = useState<SurfaceState>("loading");
  const [data, setData] = useState<AdminReferralAppealsResponse>({ appeals: [] });
  const [attributionId, setAttributionId] = useState("");
  const [appealReason, setAppealReason] = useState("");
  const [decision, setDecision] = useState<"accept" | "reject" | "correction">("accept");
  const [decisionReason, setDecisionReason] = useState("");
  const [riskType, setRiskType] = useState("device_overlap");
  const [riskSeverity, setRiskSeverity] = useState("medium");
  const [riskReason, setRiskReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAppeals = useCallback(async () => {
    const response = await adminFetch<AdminReferralAppealsResponse>("/api/v1/admin/appeals");
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
    setState(response.data.appeals.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminReferralAppealsResponse>("/api/v1/admin/appeals");
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
      setState(response.data.appeals.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submitAppeal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setResult(null);
    setError(null);
    const response = await adminFetch<AdminReferralAppeal>("/api/v1/admin/appeals", {
      method: "POST",
      body: JSON.stringify({
        attribution_id: attributionId.trim(),
        reason: appealReason.trim(),
      }),
    });
    if (!response.ok) {
      setError(response.title);
      setSubmitting(false);
      return;
    }
    setAttributionId("");
    setAppealReason("");
    setResult("邀请申诉已提交");
    await loadAppeals();
    setSubmitting(false);
  }

  async function submitDecision(event: FormEvent<HTMLFormElement>, appealId: string) {
    event.preventDefault();
    if (!canDecide) return;
    setSubmitting(true);
    setResult(null);
    setError(null);
    const response = await adminFetch<AdminReferralAppeal>(
      `/api/v1/admin/appeals/${appealId}/decision`,
      {
        method: "POST",
        body: JSON.stringify({ outcome: decision, reason: decisionReason.trim() }),
      },
    );
    if (!response.ok) {
      setError(response.title);
      setSubmitting(false);
      return;
    }
    setDecisionReason("");
    setResult("申诉决定已提交");
    await loadAppeals();
    setSubmitting(false);
  }

  async function submitRiskSignal(event: FormEvent<HTMLFormElement>, appealId: string) {
    event.preventDefault();
    if (!canRecordRisk) return;
    setSubmitting(true);
    setResult(null);
    setError(null);
    const response = await adminFetch<AdminReferralRiskSignal>(
      `/api/v1/admin/appeals/${appealId}/risk-signals`,
      {
        method: "POST",
        body: JSON.stringify({
          signal_type: riskType,
          severity: riskSeverity,
          reason: riskReason.trim(),
        }),
      },
    );
    if (!response.ok) {
      setError(response.title);
      setSubmitting(false);
      return;
    }
    setRiskReason("");
    setResult("风险信号已记录；它不会单独拒绝奖励");
    await loadAppeals();
    setSubmitting(false);
  }

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取邀请申诉…" description="只显示真实申诉、风险信号和审批事实，不展示原始识别信号。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="当前员工角色不能读取邀请申诉。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="邀请申诉平台暂不可用" description="页面保留结构，不显示虚假的申诉或审批结果。" />
    ) : state === "error" ? (
      <Status state="error" title="邀请申诉读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无邀请申诉" description="客服提交真实归因复核请求后，这里会显示申诉事实。" />
    ) : (
      <Status state="success" title="邀请申诉已接入" description="风险信号只作提示；纠错须由两位不同员工审批，并追加权益账本事件。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {result ? <Status state="success" title={result} description="服务端已完成角色、CSRF、审计和状态校验，并重新读取列表。" /> : null}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="appeals-title">
          <div className={styles.heading}>
            <div>
              <h2 id="appeals-title">邀请申诉与纠错</h2>
              <p>确定事实与风险信号分开记录；客服只能提交申请，财务审批纠错不直接改报告。</p>
            </div>
            <span className={styles.badge}>双审批</span>
          </div>
          {data.appeals.map((appeal) => (
            <article className={styles.detail} key={appeal.id} aria-labelledby={`appeal-${appeal.id}`}>
              <h3 id={`appeal-${appeal.id}`}>申诉 {appeal.id}</h3>
              <dl className={styles.facts}>
                <div><dt>归因</dt><dd>{appeal.attribution_id}</dd></div>
                <div><dt>状态</dt><dd>{statusCopy(appeal.status)}</dd></div>
                <div><dt>审批</dt><dd>审批 {appeal.approval_count}/2</dd></div>
                <div><dt>提交时间</dt><dd>{formatDate(appeal.created_at)}</dd></div>
              </dl>
              <p>申诉理由：{appeal.reason}</p>
              <p>
                风险信号：
                {appeal.risk_signals.length > 0
                  ? appeal.risk_signals.map((signal, index) => (
                      <span key={signal.id}>
                        {index > 0 ? "；" : ""}
                        {signalCopy(signal)}
                      </span>
                    ))
                  : "暂无；风险信号不会单独拒绝奖励"}
              </p>
              {appeal.correction_event_kind ? <p>纠错账本事件：{appeal.correction_event_kind}</p> : null}
              <p>未来参与限制：{appeal.participation_restriction_user_ids.length}/2</p>
              {canDecide && (appeal.status === "submitted" || appeal.status === "correction_pending") ? (
                <form className={formStyles.form} onSubmit={(event) => void submitDecision(event, appeal.id)}>
                  <label className={formStyles.field}>
                    <span>申诉决定</span>
                    <select aria-label="申诉决定" value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)}>
                      <option value="accept">接受申诉</option>
                      <option value="reject">驳回申诉</option>
                      <option value="correction">双审批纠错</option>
                    </select>
                  </label>
                  <label className={`${formStyles.field} ${formStyles.wide}`}>
                    <span>决定原因</span>
                    <input aria-label="决定原因" value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} required />
                  </label>
                  <div className={formStyles.actions}>
                    <Button type="submit" loading={submitting}>提交申诉决定</Button>
                  </div>
                </form>
              ) : null}
              {canRecordRisk && appeal.status !== "corrected" && appeal.status !== "rejected" ? (
                <form className={formStyles.form} onSubmit={(event) => void submitRiskSignal(event, appeal.id)}>
                  <label className={formStyles.field}>
                    <span>风险信号</span>
                    <select value={riskType} onChange={(event) => setRiskType(event.target.value)}>
                      <option value="ip_overlap">IP 重合</option>
                      <option value="device_overlap">设备重合</option>
                      <option value="address_overlap">地址重合</option>
                      <option value="other">其他</option>
                    </select>
                  </label>
                  <label className={formStyles.field}>
                    <span>风险等级</span>
                    <select value={riskSeverity} onChange={(event) => setRiskSeverity(event.target.value)}>
                      <option value="low">低</option>
                      <option value="medium">中</option>
                      <option value="high">高</option>
                    </select>
                  </label>
                  <label className={`${formStyles.field} ${formStyles.wide}`}>
                    <span>信号说明</span>
                    <input value={riskReason} onChange={(event) => setRiskReason(event.target.value)} required />
                  </label>
                  <div className={formStyles.actions}>
                    <Button type="submit" variant="secondary" loading={submitting}>记录风险信号</Button>
                  </div>
                </form>
              ) : null}
            </article>
          ))}
          {canSubmit ? (
            <form className={formStyles.form} onSubmit={(event) => void submitAppeal(event)}>
              <label className={formStyles.field}>
                <span>归因编号</span>
                <input value={attributionId} onChange={(event) => setAttributionId(event.target.value)} required />
              </label>
              <label className={`${formStyles.field} ${formStyles.wide}`}>
                <span>申诉理由</span>
                <input value={appealReason} onChange={(event) => setAppealReason(event.target.value)} required />
              </label>
              <div className={formStyles.actions}>
                <Button type="submit" loading={submitting}>提交邀请申诉</Button>
              </div>
            </form>
          ) : null}
          {error ? <p role="alert">{error}</p> : null}
        </section>
      ) : null}
    </div>
  );
}
