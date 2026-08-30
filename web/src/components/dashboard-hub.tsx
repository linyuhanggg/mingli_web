"use client";

import {
  ArrowRight,
  BookOpenCheck,
  CircleDotDashed,
  FileCheck2,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  getReadingResult,
  listProfiles,
  listReadings,
  type ProfileSummary,
  type ReadingVerificationSummary,
  type ReadingVersionSummary,
} from "@/lib/api";

import { useOptionalAccountSession } from "./account-session-context";
import styles from "./dashboard-hub.module.css";
import { RhythmPanel } from "./rhythm-panel";
import { StatusPanel } from "./status-panel";


type DashboardData = {
  profiles: ProfileSummary[];
  readings: ReadingVersionSummary[];
  latestAcceptedVerification: ReadingVerificationSummary | null | undefined;
};

type DashboardState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: DashboardData };

const processingStatuses = new Set<ReadingVersionSummary["status"]>([
  "input_ready",
  "prepared",
  "completing",
  "runtime_unknown",
]);

function newestByCreatedAt<T extends { created_at: string }>(items: T[]): T | null {
  return items.reduce<T | null>((latest, item) => {
    if (!latest) {
      return item;
    }
    return new Date(item.created_at).getTime() > new Date(latest.created_at).getTime()
      ? item
      : latest;
  }, null);
}

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "这次请求没有成功。";
}

function readingHref(reading: ReadingVersionSummary): string {
  return `/app/readings/${encodeURIComponent(reading.reading_version_id)}`;
}

type ContinueCardProps = {
  readings: ReadingVersionSummary[];
  latestAcceptedVerification: ReadingVerificationSummary | null | undefined;
};

function ContinueCard({ readings, latestAcceptedVerification }: ContinueCardProps) {
  const waiting = readings.filter((reading) => reading.status === "waiting_input");
  const processing = readings.filter((reading) => processingStatuses.has(reading.status));
  const needsAttention = readings.filter(
    (reading) => reading.status === "delayed" || reading.status === "terminal_stopped",
  );
  const accepted = readings.filter((reading) => reading.status === "accepted");

  const selected =
    newestByCreatedAt(waiting) ??
    newestByCreatedAt(processing) ??
    newestByCreatedAt(needsAttention) ??
    newestByCreatedAt(accepted);

  let title = "档案已就绪，可以开始第一次解读";
  let description = "从八字概览、今日与近七日里选一项；也可以独立发起一事一问。";
  let actionLabel = "查看八字概览";
  let actionHref = "/app/bazi";
  let Icon = FileCheck2;
  let tone = "ready";

  if (waiting.length > 0 && selected) {
    title = `有 ${waiting.length} 条解读等待补充信息`;
    description = "服务端已经明确列出缺少的输入，补齐后才能继续，不会偷偷代填。";
    actionLabel = "继续补充解读信息";
    actionHref = readingHref(selected);
    Icon = CircleDotDashed;
    tone = "processing";
  } else if (processing.length > 0 && selected) {
    title = `有 ${processing.length} 条解读正在处理中`;
    description = "请求已进入真实处理流程；打开详情可以查看服务端返回的最新状态。";
    actionLabel = "继续查看处理进度";
    actionHref = readingHref(selected);
    Icon = CircleDotDashed;
    tone = "processing";
  } else if (needsAttention.length > 0 && selected) {
    title = `有 ${needsAttention.length} 条解读需要你查看`;
    description = "这条解读没有正常交付；详情会保留服务端返回的停止或延迟状态。";
    actionLabel = "查看这条解读";
    actionHref = readingHref(selected);
    Icon = CircleDotDashed;
    tone = "attention";
  } else if (accepted.length > 0 && selected) {
    if (latestAcceptedVerification === null) {
      title = "最近一条解读待你核对";
      description = "正文、事实与依据已经交付；请记录符合、部分符合或不符合，反馈不会改写盘面。";
      actionLabel = "打开并完成核对";
    } else if (latestAcceptedVerification) {
      title = "最近一条解读已经完成核对";
      description = "现实反馈已经独立保存；你可以回看正文、事实与依据。";
      actionLabel = "回看这条解读";
    } else {
      title = "最近一条解读已经交付";
      description = "正文、事实与依据已经可读；打开后可以继续核对现实反馈。";
      actionLabel = "打开并核对这条解读";
    }
    actionHref = readingHref(selected);
    Icon = BookOpenCheck;
    tone = "delivered";
  }

  return (
    <article className={styles.continueCard} data-tone={tone}>
      <span className={styles.continueIcon} aria-hidden="true">
        <Icon size={23} strokeWidth={1.65} />
      </span>
      <div className={styles.continueCopy}>
        <span className={styles.kicker}>现在最值得做</span>
        <h2>{title}</h2>
        <p>{description}</p>
        <Link className={styles.primaryAction} href={actionHref}>
          <span>{actionLabel}</span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
      </div>
    </article>
  );
}

export function DashboardHub() {
  const accountSession = useOptionalAccountSession();
  const refreshAccountSession = accountSession?.refresh;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<DashboardState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    Promise.all([listProfiles(), listReadings()])
      .then(async ([profileResponse, readingResponse]) => {
        const latestAccepted = newestByCreatedAt(
          readingResponse.readings.filter((reading) => reading.status === "accepted"),
        );
        let latestAcceptedVerification: ReadingVerificationSummary | null | undefined;
        if (latestAccepted) {
          try {
            latestAcceptedVerification = (
              await getReadingResult(latestAccepted.reading_version_id)
            ).verification;
          } catch {
            // The list is still useful when the detail endpoint is temporarily unavailable.
          }
        }
        if (!cancelled) {
          setState({
            kind: "ready",
            data: {
              profiles: profileResponse.profiles,
              readings: readingResponse.readings,
              latestAcceptedVerification,
            },
          });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ kind: "error", message: readableError(error) });
          if (error instanceof ApiError && error.status === 401) {
            void refreshAccountSession?.();
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [attempt, refreshAccountSession]);

  const recoveryCopy = accountSession?.state.status === "signedIn"
    ? "已登录设备的资料读取失败，可以重新载入；若会话已经失效，再前往个人中心重新登录。"
    : !accountSession || accountSession.state.status === "signedOut"
      ? "游客会话偶尔会因网络中断失效，可以重新载入；仍失败时再前往个人中心登录。"
      : "请先重新载入；仍失败时前往个人中心确认当前设备身份。";

  const latestProfile = useMemo(
    () => state.kind === "ready" ? newestByCreatedAt(state.data.profiles) : null,
    [state],
  );

  function handleRetry() {
    setState({ kind: "loading" });
    setAttempt((value) => value + 1);
  }

  return (
    <section className={styles.hub} aria-labelledby="dashboard-title">
      <header className={styles.hubHeader}>
        <div>
          <span className={styles.kicker}>私人任务首页</span>
          <h2 id="dashboard-title">先看真实状态，再决定下一步。</h2>
        </div>
        {state.kind === "ready" ? (
          <dl className={styles.counts} aria-label="私人资料摘要">
            <div>
              <dt>档案</dt>
              <dd>{state.data.profiles.length}</dd>
            </div>
            <div>
              <dt>解读</dt>
              <dd>{state.data.readings.length}</dd>
            </div>
          </dl>
        ) : null}
      </header>

      <div className={styles.hubGrid}>
        <div className={styles.stateSlot}>
          {state.kind === "loading" ? (
            <StatusPanel
              state="loading"
              title="正在整理你的私人首页"
              description="正在读取已保存档案与最近解读，只显示服务端返回的真实记录。"
            />
          ) : null}

          {state.kind === "error" ? (
            <div className={styles.errorStack}>
              <StatusPanel
                state="error"
                title="私人首页暂时无法更新"
                description={`${state.message} ${recoveryCopy}`}
              />
              <div className={styles.recoveryActions}>
                <button className={styles.secondaryAction} type="button" onClick={handleRetry}>
                  <RefreshCw aria-hidden="true" size={17} strokeWidth={1.7} />
                  重新载入私人首页
                </button>
                <Link className={styles.textAction} href="/account">
                  前往账户
                </Link>
              </div>
            </div>
          ) : null}

          {state.kind === "ready" && !latestProfile && state.data.readings.length === 0 ? (
            <div className={styles.emptyStack}>
              <StatusPanel
                state="empty"
                title="先建立第一份命理档案"
                description="八字概览与阶段节奏都需要已确认的档案版本；不想建档时，也可以直接就一件事起卦。"
                actionHref="/account/profiles/new"
                actionLabel="建立第一份档案"
              />
              <Link className={styles.textAction} href="/app/ask/liuyao">
                不建档，直接一事一问
                <ArrowRight aria-hidden="true" size={17} strokeWidth={1.7} />
              </Link>
            </div>
          ) : null}

          {state.kind === "ready" && (latestProfile || state.data.readings.length > 0) ? (
            <ContinueCard
              readings={state.data.readings}
              latestAcceptedVerification={state.data.latestAcceptedVerification}
            />
          ) : null}
        </div>

        <RhythmPanel latestProfile={latestProfile} />
      </div>
    </section>
  );
}
