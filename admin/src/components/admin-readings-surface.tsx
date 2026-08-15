"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminReadingsResponse } from "@/lib/admin-readings";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "readingRoot", header: "任务根", sortable: true },
  { key: "version", header: "版本", sortable: true },
  { key: "stage", header: "阶段", sortable: true },
  { key: "subject", header: "受测对象" },
  { key: "capability", header: "能力", sortable: true },
  { key: "dimensions", header: "维度数", sortable: true },
  { key: "updatedAt", header: "更新时间", sortable: true },
];

const STATUS_COPY: Record<string, string> = {
  input_ready: "输入就绪",
  waiting_input: "等待输入",
  terminal_stopped: "已停止",
  prepared: "已准备",
  completing: "完成中",
  accepted: "已接受",
  delayed: "已延迟",
  runtime_unknown: "Runtime 未知",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminReadingsSurface({
  title,
  role,
}: {
  title: string;
  role?: StaffRole;
}) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminReadingsResponse>({ readings: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminReadingsResponse>(
        "/api/v1/admin/readings?limit=100",
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
      setState(response.data.readings.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.readings.map((item) => ({
    id: item.reading_version_id,
    readingRoot: item.reading_root_id,
    capability: item.capability_id,
    version: item.version,
    stage: STATUS_COPY[item.status] ?? item.status,
    subject: "—",
    dimensions: item.dimension_count,
    updatedAt: formatDate(item.created_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title={`正在读取${title}…`} description="只显示版本状态元数据，不展示出生输入或盘面正文。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="盘面与报告元数据只允许客服、运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="报告平台暂不可用" description="页面不显示虚假的盘面或报告状态。" />
    ) : state === "error" ? (
      <Status state="error" title={`${title}读取失败`} description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title={`暂无${title}`} description="创建真实 ReadingVersion 后，这里会显示版本状态。" />
    ) : (
      <Status state="success" title={`${title}已接入`} description="列表不返回 horizon、object、owner 或加密输入。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state !== "forbidden" ? <section className={styles.panel} aria-labelledby="readings-title">
        <div className={styles.heading}>
          <div>
            <h2 id="readings-title">{title}</h2>
            <p>查看 ReadingRoot、版本、阶段和维度数量；私密出生信息与受测对象不在批量索引中返回。</p>
          </div>
          <span className={styles.badge}>只读</span>
        </div>
        <Table
          caption={`${title}列表`}
          columns={COLUMNS}
          rows={rows}
          filterLabel={`筛选${title}`}
          filterPlaceholder="例如：任务根、版本、能力或阶段…"
          pageSize={20}
          emptyState={state === "unavailable" ? "服务端报告事实暂不可用" : `当前没有${title}`}
        />
      </section> : null}
    </div>
  );
}
