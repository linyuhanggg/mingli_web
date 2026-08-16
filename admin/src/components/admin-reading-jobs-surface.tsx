"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminReadingJobsResponse } from "@/lib/admin-reading-jobs";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "job", header: "任务", sortable: true },
  { key: "capability", header: "能力", sortable: true },
  { key: "product", header: "产品", sortable: true },
  { key: "version", header: "版本", sortable: true },
  { key: "readingStatus", header: "盘面态", sortable: true },
  { key: "jobStatus", header: "任务态", sortable: true },
  { key: "language", header: "语言" },
  { key: "availableAt", header: "可执行时间", sortable: true },
];

const READING_STATUS_COPY: Record<string, string> = {
  input_ready: "输入就绪",
  waiting_input: "等待输入",
  terminal_stopped: "已停止",
  prepared: "已准备",
  completing: "完成中",
  accepted: "已接受",
  delayed: "已延迟",
  runtime_unknown: "Runtime 未知",
};

const JOB_STATUS_COPY: Record<string, string> = {
  queued: "已排队",
  claimed: "已领取",
  running: "运行中",
  waiting_input: "等待输入",
  stopped: "已停止",
  complete: "已完成",
  delayed: "已延迟",
  runtime_unknown: "Runtime 未知",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminReadingJobsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminReadingJobsResponse>({ jobs: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminReadingJobsResponse>(
        "/api/v1/admin/reading-jobs?limit=100",
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
      setState(response.data.jobs.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.jobs.map((item) => ({
    id: item.id,
    job: item.id,
    capability: item.capability_id,
    product: item.product_id ?? item.capability_id,
    version: item.reading_version,
    readingStatus: READING_STATUS_COPY[item.reading_status] ?? item.reading_status,
    jobStatus: JOB_STATUS_COPY[item.job_status] ?? item.job_status,
    language: item.language,
    availableAt: formatDate(item.available_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取解读任务…" description="只显示任务状态和调度元数据，不展示输入或 lease 材料。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="解读任务只允许客服、运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="解读任务平台暂不可用" description="页面不显示虚假的任务状态。" />
    ) : state === "error" ? (
      <Status state="error" title="解读任务读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无解读任务" description="任务入队后，这里会显示真实的持久化调度状态。" />
    ) : (
      <Status state="success" title="解读任务已接入" description="不返回出生输入、输出合同、lease token 或模型 payload。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="reading-jobs-title">
          <div className={styles.heading}>
            <div>
              <h2 id="reading-jobs-title">解读任务</h2>
              <p>查看持久化任务的能力、版本、盘面态、任务态和调度时间；不展示私密输入。</p>
            </div>
            <span className={styles.badge}>只读</span>
          </div>
          <Table
            caption="解读任务列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选解读任务"
            filterPlaceholder="例如：任务 ID、能力或状态…"
            pageSize={20}
            emptyState="当前没有解读任务"
          />
        </section>
      ) : null}
    </div>
  );
}
