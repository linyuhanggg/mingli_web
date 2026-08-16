"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminCapabilitiesResponse } from "@/lib/admin-capabilities";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "capability", header: "能力", sortable: true },
  { key: "label", header: "中文名称", sortable: true },
  { key: "releaseState", header: "发布策略", sortable: true },
  { key: "audience", header: "可用范围", sortable: true },
  { key: "actions", header: "产品入口" },
];

function actionsText(actions: readonly string[]): string {
  return actions.length > 0 ? actions.join("、") : "无真实产品入口";
}

export function AdminCapabilitiesSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminCapabilitiesResponse>({
    environment: "local",
    runtime_adapter: "fake",
    runtime_health: "unverified",
    production_ready: false,
    capabilities: [],
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminCapabilitiesResponse>(
        "/api/v1/admin/capabilities?limit=100",
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
      setState(response.data.capabilities.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.capabilities.map((item) => ({
    id: item.capability_id,
    capability: item.capability_id,
    label: item.label,
    releaseState: item.release_state,
    audience: item.audience,
    actions: actionsText(item.product_actions),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取能力策略…" description="只读取版本化产品策略，不把静态策略当成 Runtime 健康或生产准入。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="能力策略只允许运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="能力策略平台暂不可用" description="页面不显示虚假的能力发布状态。" />
    ) : state === "error" ? (
      <Status state="error" title="能力策略读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无能力策略" description="注册版本化 Product Capability Policy 后，这里会显示真实策略。" />
    ) : (
      <Status state="success" title="能力策略已接入" description="PUBLIC 只表示产品策略暴露；Runtime 健康、Provider 状态和生产准入仍需独立证据。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="capabilities-title">
          <div className={styles.heading}>
            <div>
              <h2 id="capabilities-title">产品能力策略</h2>
              <p>区分对外产品入口与内部 Provider；不提供未持久化、未审计的能力发布命令。</p>
            </div>
            <span className={styles.badge}>只读策略</span>
          </div>
          <dl className={styles.summary}>
            <div className={styles.summaryItem}>
              <dt>运行环境</dt>
              <dd>{data.environment}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>Runtime adapter</dt>
              <dd>{data.runtime_adapter}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>运行时状态</dt>
              <dd>runtime_health：{data.runtime_health}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>生产证据</dt>
              <dd>生产准入：{data.production_ready ? "已验证" : "未验证"}</dd>
            </div>
          </dl>
          <Table
            caption="产品能力策略列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选能力策略"
            filterPlaceholder="例如：能力、Provider、发布策略或产品入口…"
            pageSize={20}
            emptyState="当前没有能力策略"
          />
        </section>
      ) : null}
    </div>
  );
}
