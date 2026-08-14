"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ApiError,
  listAccountHistory,
  listReadings,
  type AccountHistoryResponse,
  type ReadingVersionSummary,
} from "@/lib/api";
import {
  formatCapabilityIds,
  formatHorizon,
} from "@/lib/reading-display";

import surface from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";

import styles from "./reading-history.module.css";


const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium",
  timeStyle: "short",
});

type StatusTone = "processing" | "success" | "error";

function formatReadingTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateTimeFormatter.format(date);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "读取历史失败，请稍后重试。";
}

function statusMeta(
  status: ReadingVersionSummary["status"],
): { label: string; tone: StatusTone } {
  switch (status) {
    case "accepted":
      return { label: "已交付", tone: "success" };
    case "terminal_stopped":
      return { label: "已停止", tone: "error" };
    case "delayed":
      return { label: "交付延迟", tone: "error" };
    case "waiting_input":
      return { label: "等待输入", tone: "processing" };
    case "runtime_unknown":
      return { label: "等待确认", tone: "processing" };
    case "input_ready":
      return { label: "准备解读", tone: "processing" };
    case "prepared":
      return { label: "事实已准备", tone: "processing" };
    case "completing":
      return { label: "正在接纳正文", tone: "processing" };
  }
}

type ReadingHistoryProps = {
  readonly accountScoped?: boolean;
  readonly title?: string;
  readonly description?: string;
};

function flattenAccountHistory({ roots }: AccountHistoryResponse): ReadingVersionSummary[] {
  return roots.flatMap((root) =>
    root.versions.map((version) => toReadingVersionSummary(root, version)),
  );
}

function toReadingVersionSummary(
  root: AccountHistoryResponse["roots"][number],
  version: AccountHistoryResponse["roots"][number]["versions"][number],
): ReadingVersionSummary {
  return {
    ...version,
    profile_version_id: root.profile_version_id,
    prior_answer: null,
    input_request: null,
  };
}

export function ReadingHistory({
  accountScoped = false,
  title,
  description,
}: ReadingHistoryProps) {
  const [loading, setLoading] = useState(true);
  const [readings, setReadings] = useState<ReadingVersionSummary[] | null>(null);
  const [accountRoots, setAccountRoots] = useState<AccountHistoryResponse["roots"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const historyRequest = accountScoped
      ? listAccountHistory().then((next) => ({
          roots: next.roots,
          readings: flattenAccountHistory(next),
        }))
      : listReadings().then(({ readings: next }) => ({
          roots: null,
          readings: next,
        }));

    historyRequest
      .then(({ roots, readings: next }) => {
        if (cancelled) {
          return;
        }
        setAccountRoots(roots);
        setReadings(next);
      })
      .catch((err: unknown) => {
        if (!cancelled && err instanceof ApiError && err.status === 401) {
          setSessionExpired(true);
        } else if (!cancelled) {
          setError(errorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accountScoped, attempt]);

  function handleRetry() {
    setLoading(true);
    setError(null);
    setSessionExpired(false);
    setReadings(null);
    setAccountRoots(null);
    setAttempt((value) => value + 1);
  }

  function renderReadingEntry(entry: ReadingVersionSummary) {
    const status = statusMeta(entry.status);
    return (
      <li key={entry.reading_version_id} className={styles.historyItem}>
        <Link
          className={styles.historyLink}
          href={`/account/history/${encodeURIComponent(entry.reading_version_id)}`}
        >
          <span className={styles.historyTitle}>
            <strong>{formatCapabilityIds([entry.capability_id])}</strong>
            <span className={surface.stateTag} data-state={status.tone}>
              {status.label}
            </span>
          </span>
          <span className={styles.historyMeta}>
            <span>{formatReadingTime(entry.created_at)}</span>
            <span>版本 v{entry.version}</span>
            <span>{formatHorizon(entry.horizon)}</span>
          </span>
        </Link>
      </li>
    );
  }

  if (loading) {
    return (
      <StatusPanel
        state="loading"
        title={title ? `正在读取${title}…` : "正在读取历史…"}
        description="最近解读版本正在抵达，请稍候。"
      />
    );
  }

  if (error) {
    return (
      <>
        <StatusPanel state="error" title="无法读取历史" description={error} />
        <div className={styles.retryRow}>
          <button className={surface.secondaryButton} type="button" onClick={handleRetry}>
            重试
          </button>
        </div>
      </>
    );
  }

  if (sessionExpired) {
    return (
      <>
        <StatusPanel
          state="error"
          title="登录已过期"
          description="登录状态已失效，历史暂时无法读取；重新登录后可回到这里。"
        />
        <div className={styles.retryRow}>
          <Link className={surface.secondaryButton} href="/account">
            重新登录
          </Link>
        </div>
      </>
    );
  }

  if (readings === null || readings.length === 0) {
    return (
      <StatusPanel
        state="empty"
        title="还没有可显示的解读"
        description="服务端最多返回最近 50 条解读版本；先发起一次，真实结果才会出现在这里。"
        actionHref="/app"
        actionLabel="发起解读"
      />
    );
  }

  return (
    <section className={surface.paper} aria-labelledby="reading-history-title">
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="reading-history-title">{title ?? "最近解读版本"}</h2>
          <p>{description ?? (
            accountScoped
              ? "按 ReadingRoot 组织，每组保留真实历史版本；字段全部来自服务端公开摘要。"
              : "每条只展示解读种类、状态与创建时间，字段全部来自服务端公开摘要。"
          )}</p>
        </div>
      </div>
      {accountScoped && accountRoots ? (
        <ul className={styles.historyList}>
          {accountRoots.map((root) => (
            <li key={root.reading_root_id} className={styles.historyGroup}>
              <div className={styles.historyGroupHeader}>
                <strong>{formatCapabilityIds([root.capability_id])}任务</strong>
                <span>{root.versions.length} 个版本</span>
              </div>
              <ul className={styles.historyGroupList}>
                {root.versions.map((version) =>
                  renderReadingEntry(toReadingVersionSummary(root, version)),
                )}
              </ul>
            </li>
          ))}
        </ul>
      ) : (
        <ul className={styles.historyList}>{readings.map(renderReadingEntry)}</ul>
      )}
    </section>
  );
}
