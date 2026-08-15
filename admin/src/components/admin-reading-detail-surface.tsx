"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminReadingDetail } from "@/lib/admin-readings";

import styles from "./admin-health-surface.module.css";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminReadingDetailSurface({
  readingVersionId,
  role,
}: {
  readingVersionId: string;
  role?: StaffRole;
}) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "forbidden" | "unavailable" | "error">(
    "loading",
  );
  const [data, setData] = useState<AdminReadingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminReadingDetail>(
        `/api/v1/admin/readings/${encodeURIComponent(readingVersionId)}`,
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
      setState("ready");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, [readingVersionId]);

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取报告详情…" description="只读取版本和聚合元数据，不解密或展示报告正文。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="报告详情元数据只允许客服、运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="报告平台暂不可用" description="页面不显示虚假的报告详情或聚合计数。" />
    ) : state === "error" ? (
      <Status state="error" title="报告详情读取失败" description={error ?? "请求失败，请重试。"} />
    ) : (
      <Status state="success" title="报告详情已接入" description="详情只显示安全元数据和事实计数，不返回出生输入、horizon、object 或正文。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" && data ? (
        <section className={styles.panel} aria-labelledby="reading-detail-title">
          <div className={styles.heading}>
            <div>
              <h2 id="reading-detail-title">报告版本详情</h2>
              <p>查看 ReadingVersion 的版本事实、任务/核对计数与文档存在性；私密载荷留在服务端。</p>
            </div>
            <span className={styles.badge}>只读</span>
          </div>
          <dl className={styles.details}>
            <div>
              <dt>ReadingVersion</dt>
              <dd>{data.reading_version_id}</dd>
            </div>
            <div>
              <dt>能力</dt>
              <dd>{data.capability_id}</dd>
            </div>
            <div>
              <dt>版本</dt>
              <dd>{data.version}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{data.status}</dd>
            </div>
            <div>
              <dt>维度数</dt>
              <dd>{data.dimension_count}</dd>
            </div>
            <div>
              <dt>任务数</dt>
              <dd>{data.job_count}</dd>
            </div>
            <div>
              <dt>核对事件数</dt>
              <dd>{data.verification_event_count}</dd>
            </div>
            <div>
              <dt>文档</dt>
              <dd>{data.document_available ? "已生成" : "未生成"}</dd>
            </div>
            <div>
              <dt>创建时间</dt>
              <dd>{formatDate(data.created_at)}</dd>
            </div>
          </dl>
        </section>
      ) : null}
    </div>
  );
}
