"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminVerificationEventsResponse } from "@/lib/admin-verifications";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "source", header: "来源", sortable: true },
  { key: "reading", header: "报告版本", sortable: true },
  { key: "claim", header: "Claim" },
  { key: "outcome", header: "结果", sortable: true },
  { key: "actor", header: "操作人" },
  { key: "createdAt", header: "发生时间", sortable: true },
];

const SOURCE_COPY: Record<AdminVerificationEventsResponse["events"][number]["source"], string> = {
  reading: "整体核对",
  claim: "Claim 核对",
  feedback: "报告反馈",
};

const OUTCOME_COPY: Record<string, string> = {
  accepted: "已接受",
  partial: "部分一致",
  disagreed: "有分歧",
  unknown: "未知",
  helpful: "有帮助",
  not_helpful: "帮助有限",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminVerificationsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminVerificationEventsResponse>({ events: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminVerificationEventsResponse>(
        "/api/v1/admin/verifications?limit=100",
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
      setState(response.data.events.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.events.map((item) => ({
    id: item.id,
    source: SOURCE_COPY[item.source],
    reading: item.reading_version_id,
    claim: item.claim_id ?? "—",
    outcome: OUTCOME_COPY[item.outcome] ?? item.outcome,
    actor: item.actor_ref,
    createdAt: formatDate(item.created_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取核对事实…" description="只显示来源、结果和时间，不展示用户反馈正文。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="核对事实只允许客服、运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="核对平台暂不可用" description="页面不显示虚假的核对结果。" />
    ) : state === "error" ? (
      <Status state="error" title="核对事实读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无核对事实" description="用户提交核对或报告反馈后，这里会显示追加式事实。" />
    ) : (
      <Status state="success" title="核对事实已接入" description="整体核对、Claim 核对和报告反馈分开显示；note 不进入列表响应。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="verifications-title">
          <div className={styles.heading}>
            <div>
              <h2 id="verifications-title">核对与反馈</h2>
              <p>区分整体核对、claim-level 核对与报告反馈；只显示可审计的元数据。</p>
            </div>
            <span className={styles.badge}>只读</span>
          </div>
          <Table
            caption="核对事实列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选核对事实"
            filterPlaceholder="例如：报告版本、Claim、结果或操作人…"
            pageSize={20}
            emptyState="当前没有核对事实"
          />
        </section>
      ) : null}
    </div>
  );
}
