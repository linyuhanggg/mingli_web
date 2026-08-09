"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  getReadingResult,
  pollReading,
  type ReadingResultResponse,
  type ReadingVersionSummary,
} from "@/lib/api";
import { formatHorizon } from "@/lib/reading-display";

import { AcceptedCopy } from "./accepted-copy";
import { EvidenceList } from "./evidence-list";
import { FactPanel } from "./fact-panel";
import { FollowUpForm } from "./follow-up-form";
import { LimitNotice } from "./limit-notice";
import { NeedInputForm } from "./need-input-form";
import { VerificationForm } from "./verification-form";

import styles from "./reading-result.module.css";

const DEFAULT_POLL_MS = 2000;

function statusMeta(
  status: ReadingVersionSummary["status"],
): { label: string; text: string } {
  switch (status) {
    case "input_ready":
      return { label: "准备解读", text: "事实已就绪，正在准备解读。" };
    case "prepared":
      return { label: "事实已准备", text: "确定性事实已就绪，正在生成正文。" };
    case "completing":
      return { label: "正在接纳正文", text: "服务端正在接纳并固定正文。" };
    case "delayed":
      return { label: "交付延迟", text: "服务繁忙，正在继续处理。" };
    case "runtime_unknown":
      return {
        label: "等待确认",
        text: "运行状态暂时未知，正在等待确认。",
      };
    default:
      return { label: "处理中", text: "解读正在生成，请稍候。" };
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "读取结果失败，请稍后重试。";
}

export function ReadingResult({ readingId }: Readonly<{ readingId: string }>) {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<ReadingVersionSummary | null>(null);
  const [result, setResult] = useState<ReadingResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    function schedule(delayMs: number) {
      if (cancelled) return;
      pollTimer = setTimeout(run, delayMs);
    }

    async function run() {
      if (cancelled) return;
      try {
        const response = await pollReading(readingId);
        if (cancelled) return;
        setSummary(response);
        setError(null);
        setLoading(false);

        if (response.status === "accepted") {
          const nextResult = await getReadingResult(readingId);
          if (cancelled) return;
          setResult(nextResult);
          return;
        }

        if (
          response.status === "waiting_input" ||
          response.status === "terminal_stopped" ||
          response.status === "runtime_unknown"
        ) {
          return;
        }

        schedule(DEFAULT_POLL_MS);
      } catch (err) {
        if (cancelled) return;
        setLoading(false);
        setError(errorMessage(err));
      }
    }

    run();

    return () => {
      cancelled = true;
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [readingId, retryKey]);

  function handleRetry() {
    setLoading(true);
    setError(null);
    setSummary(null);
    setResult(null);
    setRetryKey((value) => value + 1);
  }

  function handleInputSubmitted() {
    setLoading(true);
    setError(null);
    setSummary(null);
    setResult(null);
    setRetryKey((value) => value + 1);
  }

  if (loading || (summary?.status === "accepted" && !result)) {
    return (
      <p className={styles.loading} role="status">
        正在读取结果…
      </p>
    );
  }

  if (error) {
    return (
      <div className={styles.error} role="alert">
        <p className={styles.errorMessage}>{error}</p>
        <button type="button" className={styles.retryButton} onClick={handleRetry}>
          重试
        </button>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  if (summary.status === "accepted" && result) {
    return (
      <article className={styles.result}>
        <AcceptedCopy text={result.accepted_copy} />
        <FactPanel panel={result.fact_panel} />
        <EvidenceList evidence={result.fact_panel?.evidence ?? null} />
        <LimitNotice limits={result.fact_panel?.limits ?? null} />
        <VerificationForm
          readingId={readingId}
          initialVerification={result.verification}
        />
        <FollowUpForm readingId={readingId} />
      </article>
    );
  }

  if (summary.status === "waiting_input") {
    return (
      <NeedInputForm
        readingId={readingId}
        request={summary.input_request}
        onSubmitted={handleInputSubmitted}
      />
    );
  }

  if (summary.status === "terminal_stopped") {
    return (
      <div className={styles.statusCard} role="status">
        <h2 className={styles.statusLabel}>本次解读已停止</h2>
        <p className={styles.statusText}>
          服务端已停止本次解读，请重新发起。
        </p>
        <p className={styles.actions}>
          <Link className={styles.restartLink} href="/app">
            重新发起
          </Link>
        </p>
      </div>
    );
  }

  const meta = statusMeta(summary.status);
  return (
    <div className={styles.statusCard} role="status">
      <h2 className={styles.statusLabel}>{meta.label}</h2>
      <p className={styles.statusText}>{meta.text}</p>
      <p className={styles.horizon}>目标日期：{formatHorizon(summary.horizon)}</p>
      {summary.status === "runtime_unknown" ? (
        <p className={styles.actions}>
          <button
            type="button"
            className={styles.retryButton}
            onClick={handleRetry}
          >
            重新检查状态
          </button>
        </p>
      ) : null}
    </div>
  );
}
