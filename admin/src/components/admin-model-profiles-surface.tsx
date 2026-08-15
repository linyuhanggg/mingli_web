"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminModelProfilesResponse } from "@/lib/admin-model-profiles";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "profile", header: "Model profile", sortable: true },
  { key: "provider", header: "Provider", sortable: true },
  { key: "modelVersion", header: "模型版本", sortable: true },
  { key: "outcome", header: "结果", sortable: true },
  { key: "guardErrors", header: "Guard 错误数", sortable: true },
  { key: "latency", header: "延迟 ms", sortable: true },
  { key: "policy", header: "Narrative policy", sortable: true },
  { key: "createdAt", header: "调用时间", sortable: true },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminModelProfilesSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminModelProfilesResponse>({ profiles: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminModelProfilesResponse>(
        "/api/v1/admin/model-profiles?limit=100",
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
      setState(response.data.profiles.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.profiles.map((item) => ({
    id: item.generation_attempt_id,
    profile: item.model_profile_id,
    provider: item.provider,
    modelVersion: item.provider_model_version ?? "未返回",
    outcome: item.outcome === "succeeded" ? "成功" : `失败${item.error_code ? ` · ${item.error_code}` : ""}`,
    guardErrors: item.guard_error_count,
    latency: item.latency_ms,
    policy: item.narrative_policy_version,
    createdAt: formatDate(item.created_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取 Model/Guard 回执…" description="只读取持久化调用元数据，不返回指纹、token 用量或原始 provider payload。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="Model/Guard 回执只允许运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="Model/Guard 平台暂不可用" description="页面不显示虚假的模型调用或 Guard 状态。" />
    ) : state === "error" ? (
      <Status state="error" title="Model/Guard 回执读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无 Model/Guard 回执" description="产生真实 GenerationAttempt 回执后，这里会显示安全元数据。" />
    ) : (
      <Status state="success" title="Model/Guard 回执已接入" description="列表不返回 request fingerprint、profile digest、token 数量、价格明细或出生输入。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="model-profiles-title">
          <div className={styles.heading}>
            <div>
              <h2 id="model-profiles-title">Model / Guard 调用回执</h2>
              <p>查看真实 GenerationAttempt 的模型 profile、provider、Guard 错误数和调用结果；不展示原始载荷。</p>
            </div>
            <span className={styles.badge}>只读</span>
          </div>
          <Table
            caption="Model / Guard 调用回执列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选 Model/Guard 回执"
            filterPlaceholder="例如：profile、provider、结果或 policy…"
            pageSize={20}
            emptyState="当前没有 Model/Guard 回执"
          />
        </section>
      ) : null}
    </div>
  );
}
