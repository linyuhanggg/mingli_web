"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminRuntimeReleasesResponse } from "@/lib/admin-runtime";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "name", header: "Runtime", sortable: true },
  { key: "version", header: "版本", sortable: true },
  { key: "sourceCommit", header: "Source commit", sortable: true },
  { key: "protocol", header: "协议", sortable: true },
  { key: "production", header: "生产准入", sortable: true },
  { key: "createdAt", header: "登记时间", sortable: true },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminRuntimeSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminRuntimeReleasesResponse>({ releases: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminRuntimeReleasesResponse>(
        "/api/v1/admin/runtime-releases?limit=100",
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
      setState(response.data.releases.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.releases.map((item) => ({
    id: item.id,
    name: item.name,
    version: item.version,
    sourceCommit: item.source_commit,
    protocol: item.protocol_version,
    production: item.production_ready ? "可用于生产" : "未准入",
    createdAt: formatDate(item.created_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取 Runtime 登记…" description="只读取已登记发布的安全元数据，不读取镜像或凭据内容。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="Runtime 发布元数据只允许运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="Runtime 平台暂不可用" description="页面不显示虚假的发布准入状态。" />
    ) : state === "error" ? (
      <Status state="error" title="Runtime 登记读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无 Runtime 发布登记" description="登记真实 RuntimeRelease 后，这里会显示发布元数据。" />
    ) : (
      <Status state="success" title="Runtime 发布登记已接入" description="列表不返回 manifest、image digest 或 provider 凭据。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      <section className={styles.panel} aria-labelledby="runtime-title">
        <div className={styles.heading}>
          <div>
            <h2 id="runtime-title">运行时控制面</h2>
            <p>查看实际登记的版本、协议、source commit 和生产准入；Provider 健康与密钥不在此列表中。</p>
          </div>
          <span className={styles.badge}>只读</span>
        </div>
        {state === "ready" || state === "empty" ? (
          <Table
            caption="Runtime 发布登记列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选 Runtime 发布"
            filterPlaceholder="例如：名称、版本、commit 或协议…"
            pageSize={20}
            emptyState="当前没有 Runtime 发布登记"
          />
        ) : (
          <dl className={styles.details}>
            <div>
              <dt>数据通道</dt>
              <dd>Runtime 登记服务尚未返回可核验事实</dd>
            </div>
            <div>
              <dt>当前结论</dt>
              <dd>不显示虚假的发布版本或生产准入</dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
