"use client";

import { useState } from "react";

import {
  createReadingExport,
  type ReadingExportCreateResponse,
  type ReadingExportFormat,
} from "@/lib/api";

import surface from "../app-surface.module.css";

import styles from "./reading-share-panel.module.css";

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "导出暂时无法创建，请稍后重试。";
}

function exportLabel(format: ReadingExportFormat): string {
  return format === "png" ? "高清 PNG" : "报告 PDF";
}

export function ReadingExportPanel({ readingId }: Readonly<{ readingId: string }>) {
  const [exports, setExports] = useState<Partial<Record<ReadingExportFormat, ReadingExportCreateResponse>>>({});
  const [busy, setBusy] = useState<ReadingExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const generatedExports = Object.values(exports).filter(
    (value): value is ReadingExportCreateResponse => value !== undefined,
  );
  const latestExpiry = generatedExports.at(-1)?.expires_at;

  async function createExport(format: ReadingExportFormat) {
    setBusy(format);
    setError(null);
    try {
      const created = await createReadingExport(readingId, format);
      setExports((current) => ({ ...current, [format]: created }));
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section aria-labelledby="reading-export-title" className={`${surface.paper} ${styles.panel}`}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="reading-export-title">导出报告</h2>
          <p>导出绑定当前不可变报告版本，下载链接默认 24 小时有效。</p>
        </div>
      </div>
      <div className={surface.actionRow}>
        {(["png", "pdf"] as const).map((format) => {
          const created = exports[format];
          return created ? (
            <a
              className={surface.button}
              download={created.file_name}
              href={`/api/v1/exports/${encodeURIComponent(created.token)}`}
              key={format}
            >
              下载{exportLabel(format)}
            </a>
          ) : (
            <button
              className={surface.button}
              disabled={busy !== null}
              key={format}
              onClick={() => void createExport(format)}
              type="button"
            >
              {busy === format ? "正在生成…" : exportLabel(format)}
            </button>
          );
        })}
      </div>
      {latestExpiry ? (
        <p className={styles.expiry}>
          已生成的链接有效至 {formatDateTime(latestExpiry)}，失效后可重新生成。
        </p>
      ) : null}
      {error ? <p className={styles.error} role="alert">导出失败：{error}</p> : null}
    </section>
  );
}
