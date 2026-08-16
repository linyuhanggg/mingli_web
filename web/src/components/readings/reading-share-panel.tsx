"use client";

import Link from "next/link";
import { useState } from "react";

import {
  createReadingShare,
  revokeReadingShare,
  type ReadingShareCreateResponse,
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
  return "分享暂时无法创建，请稍后重试。";
}

export function ReadingSharePanel({ readingId }: Readonly<{ readingId: string }>) {
  const [share, setShare] = useState<ReadingShareCreateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createShare() {
    setBusy(true);
    setError(null);
    try {
      setShare(await createReadingShare(readingId, 86_400));
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function revokeShare() {
    if (!share) return;
    setBusy(true);
    setError(null);
    try {
      await revokeReadingShare(readingId, share.snapshot_id);
      setShare(null);
    } catch (nextError) {
      setError(readableError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="reading-share-title" className={`${surface.paper} ${styles.panel}`}>
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="reading-share-title">分享</h2>
          <p>分享只展示服务端公开摘要，默认 24 小时有效，可随时撤销。</p>
        </div>
      </div>
      {share ? (
        <>
          <p className={styles.expiry}>有效至 {formatDateTime(share.expires_at)}</p>
          <div className={surface.actionRow}>
            <Link className={surface.button} href={`/share/${encodeURIComponent(share.token)}`}>
              打开分享页
            </Link>
            <button
              className={surface.secondaryButton}
              disabled={busy}
              onClick={() => void revokeShare()}
              type="button"
            >
              {busy ? "正在撤销…" : "撤销分享"}
            </button>
          </div>
        </>
      ) : (
        <button
          className={surface.button}
          disabled={busy}
          onClick={() => void createShare()}
          type="button"
        >
          {busy ? "正在创建…" : "创建 24 小时分享"}
        </button>
      )}
      {error ? <p className={styles.error} role="alert">分享操作失败：{error}</p> : null}
    </section>
  );
}
