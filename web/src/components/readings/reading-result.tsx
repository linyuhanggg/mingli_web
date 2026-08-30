"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  getReadingResult,
  pollReading,
  type ReadingResultResponse,
  type ReadingVersionSummary,
} from "@/lib/api";
import { shouldKeepPolling } from "@/lib/reading-poll";
import { Status, type StatusState } from "@/components/ui/status";
import {
  buildBaziChartView,
  buildBaziChartViewFromViewModel,
  formatCapabilityIds,
  formatHorizon,
} from "@/lib/reading-display";
import {
  extractFortunePeriodMarkers,
  isFortunePeriodMarkerFact,
} from "@/lib/fortune-period-markers";
import { parseTimeLayerEntitlement } from "@/lib/chart-workspace";
import surface from "@/components/app-surface.module.css";

import { AcceptedCopy } from "./accepted-copy";
import { BaziChart } from "./bazi-chart";
import { BaziDeepEntry } from "./bazi-deep-entry";
import { EvidenceList } from "./evidence-list";
import { FactPanel } from "./fact-panel";
import { FollowUpForm } from "./follow-up-form";
import { FortunePeriodTimeline } from "./fortune-period-timeline";
import { LimitNotice } from "./limit-notice";
import { LiuyaoHexagram } from "./liuyao-hexagram";
import { NeedInputForm } from "./need-input-form";
import { ReadingSharePanel } from "./reading-share-panel";
import { ReadingExportPanel } from "./reading-export-panel";
import { RuntimeChart } from "./runtime-chart";
import { VerificationForm } from "./verification-form";

const DEFAULT_POLL_MS = 2000;
const HISTORY_ESCAPE_MS = 15 * 1000;
const RESTART_ESCAPE_MS = 60 * 1000;
const POLLING_CAP_MS = 10 * 60 * 1000;
// The earlier loading label “正在读取结果” is retained here only as migration context;
// bazi synchronization now uses the frozen public wording “正在同步出盘”.
const RUNTIME_CHART_VERSIONS = new Set([
  "hecan-view/v1",
  "canwen-view/v1",
  "wenshi-view/v1",
  "bazi-relationship/v1",
  "ziwei-relationship/v1",
  "qizheng-relationship/v1",
  "ziwei-chart/v1",
  "qizheng-chart/v1",
  "luming-nayin-chart/v1",
  "rhythm-facts-view/v1",
  "taiyi-chart/v1",
  "selection-chart/v1",
  "fengshui-view/v1",
  "liuyao-chart/v1",
  "meihua-chart/v1",
  "qimen-chart/v1",
  "daliuren-chart/v1",
  "physiognomy-view/v1",
  "five-elements-facts-view/v1",
  "fortune-facts-view/v1",
  "chart-similarity-view/v1",
  "time-check-view/v1",
]);
const CROSS_ART_PRODUCT_IDS = new Set(["hecan", "canwen", "wenshi"]);
const RELATIONSHIP_PRODUCT_IDS = new Set([
  "bazi-relationship",
  "ziwei-relationship",
  "qizheng-relationship",
]);
const RESULT_READY_STATUSES = new Set(["prepared", "completing", "accepted"]);

function validStartedAt(value: number | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function elapsedSince(startedAt: number): number {
  return Math.max(0, Date.now() - startedAt);
}

function serverStartedAt(value: string | undefined): number | null {
  const parsed = typeof value === "string" ? Date.parse(value) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

type StatusTone = "processing" | "success" | "error";

function statusMeta(
  status: ReadingVersionSummary["status"],
): { label: string; text: string; tone: StatusTone } {
  switch (status) {
    case "input_ready":
      return {
        label: "准备解读",
        text: "事实已就绪，正在准备解读。",
        tone: "processing",
      };
    case "prepared":
      return {
        label: "事实已准备",
        text: "确定性事实已就绪，正在生成正文。",
        tone: "processing",
      };
    case "completing":
      return {
        label: "正在接纳正文",
        text: "服务端正在接纳并固定正文。",
        tone: "processing",
      };
    case "delayed":
      return {
        label: "交付延迟",
        text: "服务繁忙，正在继续处理。",
        tone: "processing",
      };
    case "waiting_input":
      return {
        label: "等待输入",
        text: "需要补充结构化资料后才能继续。",
        tone: "processing",
      };
    case "terminal_stopped":
      return {
        label: "已停止",
        text: "服务端已停止本次解读，请重新发起。",
        tone: "error",
      };
    case "accepted":
      return {
        label: "已交付",
        text: "正文已接纳并固定，可随时回看。",
        tone: "success",
      };
    case "runtime_unknown":
      return {
        label: "等待确认",
        text: "运行状态暂时未知，正在等待确认。",
        tone: "processing",
      };
    default:
      return {
        label: "处理中",
        text: "解读正在生成，请稍候。",
        tone: "processing",
      };
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "读取结果失败，请稍后重试。";
}

function resultErrorState(error: unknown): {
  state: Extract<StatusState, "error" | "unauthorized" | "unavailable" | "empty">;
  title: string;
  description: string;
} {
  const description = errorMessage(error);
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return {
        state: "unauthorized",
        title: "需要登录才能看这份结果",
        description: description || "登录后才能查看这份结果；不会重复提交出生资料。",
      };
    }
    if (error.status === 404) {
      return {
        state: "empty",
        title: "还没有可展示的盘面",
        description: "这份结果不存在或不属于当前会话，不会用演示数据填满。",
      };
    }
    if (error.status === 503) {
      return {
        state: "unavailable",
        title: "结果服务暂时不可用，不会展示未确认内容",
        description: description || "当前结果服务暂不可用，不会展示未确认内容。",
      };
    }
  }
  return { state: "error", title: "读取失败，请重试", description };
}

function ArchiveRail({
  readingId,
  summary,
  result,
}: Readonly<{
  readingId: string;
  summary: ReadingVersionSummary;
  result: ReadingResultResponse | null;
}>) {
  const meta = statusMeta(summary.status);

  return (
    <aside className={surface.evidenceRail} aria-labelledby="reading-summary-title">
      <div className={surface.rail}>
        <h2 id="reading-summary-title">报告信息</h2>
        <dl className={surface.railMeta}>
          <div>
            <dt>报告版本</dt>
            <dd>v{summary.version}</dd>
          </div>
        </dl>
        <p className={surface.railTagRow}>
          <span className={surface.stateTag} data-state={meta.tone}>
            {meta.label}
          </span>
        </p>
        <p className={surface.railNote}>
          这份报告保留当前版本，后续修改不会覆盖本次内容。
        </p>
      </div>
      {summary.status === "accepted" && result?.document?.actions.share.enabled === true ? (
        <ReadingSharePanel readingId={readingId} />
      ) : null}
      {summary.status === "accepted" && result?.document?.actions.export.enabled === true ? (
        <ReadingExportPanel readingId={readingId} />
      ) : null}
    </aside>
  );
}

function WaitingStatus({
  context,
  elapsedMs,
  onRestart,
  onRetry,
}: Readonly<{
  context?: string;
  elapsedMs: number;
  onRestart?: () => void;
  onRetry: () => void;
}>) {
  const canLeaveForHistory = elapsedMs >= HISTORY_ESCAPE_MS;
  const canRestart = elapsedMs >= RESTART_ESCAPE_MS;
  const pollingEnded = elapsedMs >= POLLING_CAP_MS;
  const title = pollingEnded
    ? "自动检查已暂停"
    : canRestart
      ? "这次排盘比平时久"
      : canLeaveForHistory
        ? "仍在认真排盘"
        : "正在同步出盘";
  const description = pollingEnded
    ? "服务器上的任务仍然保留；可以手动检查当前任务，或稍后从推演历史查看。"
    : canRestart
      ? "可能服务繁忙；原资料不会丢，可以换一个新任务重新发起，当前任务也仍会保留。"
      : canLeaveForHistory
        ? "自动检查仍在继续。你可以离开，完成后从推演历史查看。"
        : "正在准备定位、时间层与盘面事实；完成后直接进入结果。";

  return (
    <Status
      actions={canLeaveForHistory ? (
        <>
          {canRestart && onRestart ? (
            <button type="button" onClick={onRestart}>
              重试（保留原资料）
            </button>
          ) : null}
          {pollingEnded ? (
            <button data-variant="secondary" type="button" onClick={onRetry}>
              重新检查状态
            </button>
          ) : null}
          <Link data-variant="secondary" href="/account/history">
            稍后查看
          </Link>
        </>
      ) : null}
      description={context ? `${description} ${context}` : description}
      state="loading"
      title={title}
    />
  );
}

export type ReadingResultProps = Readonly<{
  baziDeepFulfilled?: boolean;
  headingLevel?: 1 | 2;
  onPollError?: (error: unknown) => void;
  onRestart?: () => void;
  onSummary?: (summary: ReadingVersionSummary) => void;
  readingId: string;
  startedAt?: number;
}>;

export function ReadingResult(props: ReadingResultProps) {
  const instanceKey = `${props.readingId}:${props.startedAt ?? "fresh"}`;
  return <ReadingResultForVersion key={instanceKey} {...props} />;
}

function ReadingResultForVersion({
  readingId,
  baziDeepFulfilled = false,
  headingLevel = 1,
  onPollError,
  onRestart,
  onSummary,
  startedAt,
}: ReadingResultProps) {
  const ResultHeading = headingLevel === 2 ? "h2" : "h1";
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<ReadingVersionSummary | null>(null);
  const [result, setResult] = useState<ReadingResultResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [timerStartedAt, setTimerStartedAt] = useState(
    () => (validStartedAt(startedAt) ? startedAt : Date.now()),
  );
  const [elapsedMs, setElapsedMs] = useState(0);
  const timerStartedAtRef = useRef(timerStartedAt);
  const supplementalWindowStartedAtRef = useRef<number | null>(null);
  const automaticPollControllerRef = useRef<AbortController | null>(null);
  const automaticPollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onPollErrorRef = useRef(onPollError);
  const onSummaryRef = useRef(onSummary);

  useEffect(() => {
    onPollErrorRef.current = onPollError;
    onSummaryRef.current = onSummary;
  }, [onPollError, onSummary]);

  useEffect(() => {
    const updateElapsed = () => setElapsedMs(elapsedSince(timerStartedAt));
    const stopAutomaticPolling = () => {
      const activeTimer = automaticPollTimerRef.current;
      if (activeTimer !== null) {
        clearTimeout(activeTimer);
        automaticPollTimerRef.current = null;
      }
      const activeController = automaticPollControllerRef.current;
      automaticPollControllerRef.current = null;
      activeController?.abort();
      updateElapsed();
    };
    const currentElapsed = elapsedSince(timerStartedAt);
    if (currentElapsed >= POLLING_CAP_MS) {
      stopAutomaticPolling();
    }
    const boundaryTimers = [HISTORY_ESCAPE_MS, RESTART_ESCAPE_MS, POLLING_CAP_MS]
      .filter((boundary) => boundary > currentElapsed)
      .map((boundary) => window.setTimeout(
        boundary === POLLING_CAP_MS ? stopAutomaticPolling : updateElapsed,
        boundary - currentElapsed,
      ));
    const elapsedTimer = window.setInterval(updateElapsed, 1000);
    if (currentElapsed < POLLING_CAP_MS) {
      updateElapsed();
    }

    return () => {
      for (const timer of boundaryTimers) window.clearTimeout(timer);
      window.clearInterval(elapsedTimer);
    };
  }, [timerStartedAt]);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    const pollController = new AbortController();
    const elapsed = elapsedSince(timerStartedAtRef.current);
    const automaticRun = elapsed < POLLING_CAP_MS;
    const manualAtCap = !automaticRun && retryKey > 0;

    if (automaticRun) {
      automaticPollControllerRef.current = pollController;
    }

    function setRunTimer(callback: () => void, delayMs: number) {
      const nextTimer = setTimeout(() => {
        if (pollTimer === nextTimer) {
          pollTimer = null;
        }
        if (automaticPollTimerRef.current === nextTimer) {
          automaticPollTimerRef.current = null;
        }
        callback();
      }, delayMs);
      pollTimer = nextTimer;
      if (automaticRun) {
        automaticPollTimerRef.current = nextTimer;
      }
    }

    function schedule(delayMs: number) {
      if (cancelled || manualAtCap || pollController.signal.aborted) return;
      const remaining = POLLING_CAP_MS - elapsedSince(timerStartedAtRef.current);
      if (remaining <= 0) return;
      setRunTimer(() => void run(false), Math.min(delayMs, remaining));
    }

    async function run(manualAtCap: boolean) {
      if (
        cancelled
        || pollController.signal.aborted
        || (!manualAtCap && elapsedSince(timerStartedAtRef.current) >= POLLING_CAP_MS)
      ) {
        return;
      }
      try {
        const response = await pollReading(readingId, pollController.signal);
        if (cancelled || pollController.signal.aborted) return;
        const authoritativeStartedAt = serverStartedAt(response.created_at);
        const applyAuthoritativeStartedAt = () => {
          if (
            supplementalWindowStartedAtRef.current === null
            && authoritativeStartedAt !== null
            && authoritativeStartedAt !== timerStartedAtRef.current
          ) {
            timerStartedAtRef.current = authoritativeStartedAt;
            setTimerStartedAt(authoritativeStartedAt);
          }
        };
        setSummary(response);
        setError(null);
        setLoading(false);
        onSummaryRef.current?.(response);

        if (RESULT_READY_STATUSES.has(response.status) || response.result_available) {
          const nextResult = await getReadingResult(readingId, pollController.signal);
          if (cancelled || pollController.signal.aborted) return;
          setResult(nextResult);
          if (!shouldKeepPolling({
            status: nextResult.status,
            poll_required: nextResult.poll_required ?? response.poll_required,
          })) {
            if (nextResult.status === "accepted" && response.status !== "accepted") {
              try {
                const finalSummary = await pollReading(readingId, pollController.signal);
                if (cancelled || pollController.signal.aborted) return;
                setSummary(finalSummary);
                onSummaryRef.current?.(finalSummary);
                applyAuthoritativeStartedAt();
                if (shouldKeepPolling(finalSummary)) {
                  schedule(
                    finalSummary.poll_after_seconds != null
                      ? finalSummary.poll_after_seconds * 1000
                      : DEFAULT_POLL_MS,
                  );
                }
              } catch {
                if (cancelled || pollController.signal.aborted) return;
                applyAuthoritativeStartedAt();
                schedule(
                  response.poll_after_seconds != null
                    ? response.poll_after_seconds * 1000
                  : DEFAULT_POLL_MS,
                );
              }
            } else {
              applyAuthoritativeStartedAt();
            }
            return;
          }
          applyAuthoritativeStartedAt();
          schedule(
            (nextResult.poll_after_seconds ?? response.poll_after_seconds) != null
              ? (nextResult.poll_after_seconds ?? response.poll_after_seconds ?? 0) * 1000
              : DEFAULT_POLL_MS,
          );
          return;
        }

        applyAuthoritativeStartedAt();
        if (!shouldKeepPolling(response)) {
          return;
        }

        schedule(response.poll_after_seconds != null
          ? response.poll_after_seconds * 1000
          : DEFAULT_POLL_MS);
      } catch (err) {
        if (cancelled || pollController.signal.aborted) return;
        setLoading(false);
        setError(err);
        onPollErrorRef.current?.(err);
      }
    }

    if (automaticRun || manualAtCap) {
      // Let a development StrictMode probe clean up before it creates a request.
      setRunTimer(() => void run(manualAtCap), 0);
    }

    return () => {
      cancelled = true;
      if (automaticPollControllerRef.current === pollController) {
        automaticPollControllerRef.current = null;
      }
      pollController.abort();
      if (pollTimer) {
        clearTimeout(pollTimer);
        if (automaticPollTimerRef.current === pollTimer) {
          automaticPollTimerRef.current = null;
        }
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
    const nextStartedAt = Date.now();
    supplementalWindowStartedAtRef.current = nextStartedAt;
    timerStartedAtRef.current = nextStartedAt;
    setTimerStartedAt(nextStartedAt);
    setElapsedMs(0);
    setLoading(true);
    setError(null);
    setSummary(null);
    setResult(null);
    setRetryKey((value) => value + 1);
  }

  if (error) {
    const meta = resultErrorState(error);
    return (
      <article className={surface.readingBody}>
        <Status
          actions={
            meta.state === "unauthorized" ? (
              <Link href="/auth/login">登录后继续</Link>
            ) : (
              <button type="button" onClick={handleRetry}>
                重试
              </button>
            )
          }
          description={meta.description}
          state={meta.state}
          title={meta.title}
        />
      </article>
    );
  }

  if (
    loading ||
    (summary && RESULT_READY_STATUSES.has(summary.status) && !result)
  ) {
    return (
      <article className={surface.readingBody}>
        <WaitingStatus
          elapsedMs={elapsedMs}
          onRestart={onRestart}
          onRetry={handleRetry}
        />
      </article>
    );
  }

  if (!summary) {
    return (
      <article className={surface.readingBody}>
        <Status
          actions={(
            <button type="button" onClick={handleRetry}>
              重试
            </button>
          )}
          description="服务端尚未返回可展示的公开摘要，不会用演示数据填满结果。"
          state="empty"
          title="还没有可展示的盘面"
        />
      </article>
    );
  }

  if (RESULT_READY_STATUSES.has(summary.status) && result) {
    const isAccepted = summary.status === "accepted";
    const canFollowUp = isAccepted && result.document?.actions.follow_up.enabled === true;
    const productId = summary.product_id;
    const isRuntimeCrossArt =
      (typeof productId === "string" && CROSS_ART_PRODUCT_IDS.has(productId)) ||
      result.view_model?.schema_version === "hecan-view/v1" ||
      result.view_model?.schema_version === "canwen-view/v1";
    const isRelationship =
      (typeof productId === "string" && RELATIONSHIP_PRODUCT_IDS.has(productId)) ||
      (result.view_model?.schema_version.endsWith("-relationship/v1") ?? false);
    const isFiveElementsFacts =
      result.view_model?.schema_version === "five-elements-facts-view/v1";
    const isChartSimilarity =
      summary.product_id === "chart-similarity" ||
      result.view_model?.schema_version === "chart-similarity-view/v1";
    const isBazi =
      summary.capability_id === "bazi" &&
      !isRuntimeCrossArt &&
      !isRelationship &&
      !isFiveElementsFacts &&
      !isChartSimilarity;
    const isZiweiNatal =
      !isRuntimeCrossArt &&
      !isRelationship &&
      !isFiveElementsFacts &&
      !isChartSimilarity &&
      (summary.capability_id === "ziwei" ||
        summary.product_id === "ziwei" ||
        result.view_model?.schema_version === "ziwei-chart/v1");
    const isQizhengNatal =
      !isRuntimeCrossArt &&
      !isRelationship &&
      !isFiveElementsFacts &&
      !isChartSimilarity &&
      (summary.capability_id === "qizheng" ||
        summary.product_id === "qizheng" ||
        result.view_model?.schema_version === "qizheng-chart/v1");
    const isNatalChart = isBazi || isZiweiNatal || isQizhengNatal;
    // A missing projection is C only for a route that actually depends on a
    // Runtime ViewModel. Plain legacy result pages do not have this gate.
    const requiresCapabilityProjection = isBazi || result.view_model != null;
    const capabilityTier =
      result.capability?.tier ?? (requiresCapabilityProjection ? "C" : null);
    const showRuntimeChart = capabilityTier === "A" || capabilityTier === "B";
    const isFortune = summary.capability_id === "fortune";
    const isLiuyao = summary.capability_id === "liuyao";
    const isQimen = summary.capability_id === "qimen";
    const isDaliuren = summary.capability_id === "daliuren";
    const hasTypedLiuyao = result.view_model?.schema_version === "liuyao-chart/v1";
    const hasRawLiuyao = isLiuyao && !hasTypedLiuyao;
    const hasRuntimeChart = Boolean(
      result.view_model && RUNTIME_CHART_VERSIONS.has(result.view_model.schema_version),
    );
    const publicFacts = result.fact_panel?.facts ?? [];
    const chart =
      isBazi && capabilityTier !== "C"
        ? result.view_model?.schema_version === "bazi-chart/v1"
          ? buildBaziChartViewFromViewModel(result.view_model)
          : buildBaziChartView(publicFacts)
        : null;
    const timeLayerEntitlement = isBazi
      ? parseTimeLayerEntitlement(result.time_layer_entitlement)
      : null;
    const runtimeTimeLayerEntitlement = isZiweiNatal
      ? result.time_layer_entitlement
      : null;
    const fortuneMarkers = isFortune
      ? extractFortunePeriodMarkers(publicFacts)
      : [];
    const hasFortuneTimeline = fortuneMarkers.length > 0;
    const generalFactPanel =
      isFortune && result.fact_panel
        ? {
            ...result.fact_panel,
            facts: result.fact_panel.facts.filter(
              (fact) => !isFortunePeriodMarkerFact(fact),
            ),
          }
        : result.fact_panel;
    const question = result.fact_panel?.question ?? "本次解读";
    const scopeLabel =
      summary.product_id === "hecan"
        ? "命盘合参"
        : summary.product_id === "canwen"
          ? "多盘问答"
          : summary.product_id === "bazi-relationship"
            ? "八字合盘"
            : summary.product_id === "ziwei-relationship"
              ? "紫微合盘"
          : summary.product_id === "qizheng-relationship"
            ? "七政合盘"
            : summary.product_id === "five-elements-facts"
              ? "五行事实与调候依据"
          : summary.product_id === "rhythm"
            ? "本命音律事实"
          : summary.product_id === "chart-similarity"
            ? "八字同盘四柱事实比较"
          : formatCapabilityIds([summary.capability_id]);

    // GET /result 200: view_model+document empty/null, or source_status=unavailable
    // → unavailable. Do not wait for GET 503. If accepted_copy or fact_panel is
    // present, keep the generic ReadingResult (no invented relationship_signals).
    const emptyResultPayload =
      result.view_model == null &&
      result.accepted_copy == null &&
      result.document == null &&
      result.fact_panel == null;
    const sourceUnavailable = result.capability?.source_status === "unavailable";
    if (sourceUnavailable || emptyResultPayload) {
      return (
        <article className={surface.readingBody}>
          <Status
            actions={(
              <button type="button" onClick={handleRetry}>
                重试
              </button>
            )}
            description="当前结果服务暂不可用，不会展示未确认内容。"
            state="unavailable"
            title="结果服务暂时不可用，不会展示未确认内容"
          />
        </article>
      );
    }

    if (!isNatalChart && !isFortune && !isLiuyao && !isQimen && !isDaliuren) {
      return (
        <div className={surface.readingLayout}>
          <article className={surface.readingBody} aria-label="解读正文">
            <header className={surface.readingHeader}>
              <h2>{question}</h2>
              <p>
                {scopeLabel} · 目标日期 {formatHorizon(summary.horizon)} · 版本 v
                {summary.version}
              </p>
            </header>

            <section
              className={surface.readingSection}
              aria-labelledby="reading-judgment-title"
            >
              <span className={surface.sectionIndex} aria-hidden="true">
                01
              </span>
              <div>
                <h2 id="reading-judgment-title">判断</h2>
                <AcceptedCopy text={result.accepted_copy} />
              </div>
            </section>

            {hasFortuneTimeline ? (
              <section
                className={surface.readingSection}
                aria-labelledby="reading-fortune-period-title"
              >
                <span className={surface.sectionIndex} aria-hidden="true">
                  02
                </span>
                <div>
                  <h2 id="reading-fortune-period-title">
                    {summary.horizon.kind_id === "week" ? "近七日周期" : "周期标记"}
                  </h2>
                  <FortunePeriodTimeline markers={fortuneMarkers} />
                </div>
              </section>
            ) : null}

            {hasRawLiuyao ? (
              <section
                className={surface.readingSection}
                aria-labelledby="reading-liuyao-title"
              >
                <span className={surface.sectionIndex} aria-hidden="true">
                  02
                </span>
                <div>
                  <h2 id="reading-liuyao-title">盘面事实</h2>
                  <p className={surface.inlineNote}>
                    本卦、变卦与六个爻位只复述服务端公开事实，浏览器不重新起卦。
                  </p>
                  <LiuyaoHexagram
                    facts={result.fact_panel?.facts ?? []}
                    evidence={result.fact_panel?.evidence ?? []}
                  />
                </div>
              </section>
            ) : null}

            {hasRuntimeChart && result.view_model && showRuntimeChart ? (
              <section
                className={surface.readingSection}
                aria-labelledby="reading-runtime-chart-title"
              >
                <span className={surface.sectionIndex} aria-hidden="true">
                  {String(2 + (hasFortuneTimeline ? 1 : 0) + (hasRawLiuyao ? 1 : 0)).padStart(2, "0")}
                </span>
                <div>
                  <h2 id="reading-runtime-chart-title">盘面事实</h2>
                  <p className={surface.inlineNote}>
                    盘面由服务端排定；浏览器只负责展示，不重新计算。
                  </p>
                  {capabilityTier === "B" ? (
                    <p className={surface.inlineNote} data-capability-tier="B">
                      当前只提供确定性盘面与事实，不提供断语。
                    </p>
                  ) : null}
                  <RuntimeChart
                    viewModel={result.view_model}
                    capability={result.capability}
                    timeLayerEntitlement={runtimeTimeLayerEntitlement}
                  />
                </div>
              </section>
            ) : null}

            {capabilityTier === "C" ? (
              <p className={surface.inlineNote} data-capability-tier="C">
                当前能力仍在适配中，暂不展示未确认的盘面或断法。
              </p>
            ) : null}

            <section
              className={surface.readingSection}
              aria-labelledby="reading-fact-title"
            >
              <span className={surface.sectionIndex} aria-hidden="true">
                {String(2 + (hasFortuneTimeline ? 1 : 0) + (hasRawLiuyao ? 1 : 0) + (hasRuntimeChart ? 1 : 0)).padStart(2, "0")}
              </span>
              <div>
                <h2 id="reading-fact-title">事实</h2>
                <FactPanel panel={generalFactPanel} />
              </div>
            </section>

            <section
              className={surface.readingSection}
              aria-labelledby="reading-evidence-title"
            >
              <span className={surface.sectionIndex} aria-hidden="true">
                {String(3 + (hasFortuneTimeline ? 1 : 0) + (hasRawLiuyao ? 1 : 0) + (hasRuntimeChart ? 1 : 0)).padStart(2, "0")}
              </span>
              <div>
                <h2 id="reading-evidence-title">依据与边界</h2>
                <EvidenceList
                  evidence={result.fact_panel?.evidence ?? null}
                  facts={result.fact_panel?.facts ?? []}
                />
                <LimitNotice limits={result.fact_panel?.limits ?? null} />
              </div>
            </section>

            {isAccepted ? (
              <section
                className={surface.readingSection}
                aria-labelledby="reading-review-title"
              >
                <span className={surface.sectionIndex} aria-hidden="true">
                  {String(4 + (hasFortuneTimeline ? 1 : 0) + (hasRawLiuyao ? 1 : 0) + (hasRuntimeChart ? 1 : 0)).padStart(2, "0")}
                </span>
                <div>
                  <h2 id="reading-review-title">复核与追问</h2>
                  <VerificationForm
                    readingId={readingId}
                    initialVerification={result.verification}
                  />
                  {canFollowUp ? <FollowUpForm readingId={readingId} /> : null}
                </div>
              </section>
            ) : null}
          </article>
          <ArchiveRail readingId={readingId} summary={summary} result={result} />
        </div>
      );
    }

    if (isFortune || isLiuyao) {
      const pageTitle = isFortune ? "运势" : "六爻";
      const pageIntro = isFortune
        ? "只展示已返回的周期与事实。"
        : "只展示已返回的卦象事实。";
      const typedFortuneReady =
        capabilityTier !== "C" &&
        showRuntimeChart &&
        result.view_model?.schema_version === "fortune-facts-view/v1";
      const typedLiuyaoReady =
        capabilityTier !== "C" &&
        showRuntimeChart &&
        hasTypedLiuyao &&
        result.view_model != null;
      const remainingFacts = generalFactPanel?.facts ?? [];
      const hasExactCitation = (result.fact_panel?.evidence ?? []).length > 0;
      const hasPlate =
        hasFortuneTimeline ||
        hasRawLiuyao ||
        typedFortuneReady ||
        typedLiuyaoReady ||
        remainingFacts.length > 0 ||
        result.accepted_copy != null ||
        hasExactCitation;

      return (
        <div className={surface.readingLayout}>
          <article className={surface.readingBody} aria-label="解读正文">
            <header className={surface.readingHeader}>
              <ResultHeading>{pageTitle}</ResultHeading>
              <p>
                {pageIntro} 目标日期 {formatHorizon(summary.horizon)}。
              </p>
            </header>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-workspace-title"
            >
              <div>
                <h2 id="reading-workspace-title">排盘结果</h2>
                {capabilityTier === "C" ? (
                  <Status
                    description="当前能力暂不可用，不会展示未确认的盘面或断法。"
                    state="unavailable"
                    title="结果服务暂时不可用，不会展示未确认内容"
                  />
                ) : !hasPlate ? (
                  <Status
                    description="服务端尚未返回可展示的盘面事实，不会伪造盘面。"
                    state="empty"
                    title="还没有可展示的盘面"
                  />
                ) : (
                  <>
                    <EvidenceList
                      exactOnly
                      evidence={result.fact_panel?.evidence ?? []}
                      facts={result.fact_panel?.facts ?? []}
                    />
                    {hasFortuneTimeline ? (
                      <section aria-labelledby="reading-fortune-period-title">
                        <h2 id="reading-fortune-period-title">
                          {summary.horizon.kind_id === "week" ? "近七日周期" : "周期标记"}
                        </h2>
                        <FortunePeriodTimeline markers={fortuneMarkers} />
                      </section>
                    ) : null}
                    {hasRawLiuyao ? (
                      <>
                        <p className={surface.inlineNote}>
                          本卦、变卦与六个爻位只复述服务端公开事实，浏览器不重新起卦。
                        </p>
                        <LiuyaoHexagram
                          facts={result.fact_panel?.facts ?? []}
                          evidence={result.fact_panel?.evidence ?? []}
                        />
                      </>
                    ) : null}
                    {(typedFortuneReady || typedLiuyaoReady) && result.view_model ? (
                      <RuntimeChart
                        viewModel={result.view_model}
                        capability={result.capability}
                        timeLayerEntitlement={runtimeTimeLayerEntitlement}
                      />
                    ) : null}
                    {generalFactPanel && remainingFacts.length > 0 ? (
                      <section aria-labelledby="reading-fact-title">
                        <h2 id="reading-fact-title">事实</h2>
                        <FactPanel panel={generalFactPanel} />
                      </section>
                    ) : null}
                    {result.accepted_copy ? (
                      <section aria-labelledby="reading-judgment-title">
                        <h2 id="reading-judgment-title">判断</h2>
                        <AcceptedCopy text={result.accepted_copy} />
                      </section>
                    ) : null}
                  </>
                )}
              </div>
            </section>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-evidence-title"
            >
              <div>
                <h2 id="reading-evidence-title">依据与边界</h2>
                <EvidenceList
                  evidence={result.fact_panel?.evidence ?? null}
                  facts={result.fact_panel?.facts ?? []}
                />
                <LimitNotice limits={result.fact_panel?.limits ?? null} />
              </div>
            </section>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-note-title"
            >
              <div>
                <h2 id="reading-note-title">阅读说明</h2>
                <p className={surface.inlineNote}>
                  只提供已返回的盘面与确定性事实，不在页面编写判断。
                </p>
              </div>
            </section>

            {isAccepted ? (
              <section
                className={surface.readingSection}
                data-layout="full-width-reading-section"
                aria-labelledby="reading-review-title"
              >
                <div>
                  <h2 id="reading-review-title">复核与追问</h2>
                  <VerificationForm
                    readingId={readingId}
                    initialVerification={result.verification}
                  />
                  {canFollowUp ? <FollowUpForm readingId={readingId} /> : null}
                </div>
              </section>
            ) : null}
          </article>
          <ArchiveRail readingId={readingId} summary={summary} result={result} />
        </div>
      );
    }

    if (isQimen || isDaliuren) {
      const pageTitle = isQimen ? "奇门" : "大六壬";
      const pageIntro = isQimen
        ? "只展示已返回的九宫盘面事实。"
        : "只展示已返回的四课三传事实。";
      const typedReady =
        capabilityTier !== "C" &&
        showRuntimeChart &&
        result.view_model != null &&
        (isQimen
          ? result.view_model.schema_version === "qimen-chart/v1"
          : result.view_model.schema_version === "daliuren-chart/v1");
      const remainingFacts = result.fact_panel?.facts ?? [];
      const hasExactCitation = (result.fact_panel?.evidence ?? []).length > 0;
      const hasPlate =
        typedReady ||
        remainingFacts.length > 0 ||
        result.accepted_copy != null ||
        hasExactCitation;

      return (
        <div className={surface.readingLayout}>
          <article className={surface.readingBody} aria-label="解读正文">
            <header className={surface.readingHeader}>
              <ResultHeading>{pageTitle}</ResultHeading>
              <p>
                {pageIntro} 目标日期 {formatHorizon(summary.horizon)}。
              </p>
            </header>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-workspace-title"
            >
              <div>
                <h2 id="reading-workspace-title">排盘结果</h2>
                {capabilityTier === "C" ? (
                  <Status
                    description="当前能力暂不可用，不会展示未确认的盘面或断法。"
                    state="unavailable"
                    title="结果服务暂时不可用，不会展示未确认内容"
                  />
                ) : !hasPlate ? (
                  <Status
                    description="服务端尚未返回可展示的盘面事实，不会伪造盘面。"
                    state="empty"
                    title="还没有可展示的盘面"
                  />
                ) : (
                  <>
                    <EvidenceList
                      exactOnly
                      evidence={result.fact_panel?.evidence ?? []}
                      facts={result.fact_panel?.facts ?? []}
                    />
                    {typedReady && result.view_model ? (
                      <RuntimeChart
                        viewModel={result.view_model}
                        capability={result.capability}
                        timeLayerEntitlement={runtimeTimeLayerEntitlement}
                      />
                    ) : null}
                    {remainingFacts.length > 0 ? (
                      <section aria-labelledby="reading-fact-title">
                        <h2 id="reading-fact-title">事实</h2>
                        <FactPanel panel={result.fact_panel!} />
                      </section>
                    ) : null}
                    {result.accepted_copy ? (
                      <section aria-labelledby="reading-judgment-title">
                        <h2 id="reading-judgment-title">判断</h2>
                        <AcceptedCopy text={result.accepted_copy} />
                      </section>
                    ) : null}
                  </>
                )}
              </div>
            </section>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-evidence-title"
            >
              <div>
                <h2 id="reading-evidence-title">依据与边界</h2>
                <EvidenceList
                  evidence={result.fact_panel?.evidence ?? null}
                  facts={result.fact_panel?.facts ?? []}
                />
                <LimitNotice limits={result.fact_panel?.limits ?? null} />
              </div>
            </section>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-note-title"
            >
              <div>
                <h2 id="reading-note-title">阅读说明</h2>
                <p className={surface.inlineNote}>
                  只提供已返回的盘面与确定性事实，不在页面编写判断。
                </p>
              </div>
            </section>

            {isAccepted ? (
              <section
                className={surface.readingSection}
                data-layout="full-width-reading-section"
                aria-labelledby="reading-review-title"
              >
                <div>
                  <h2 id="reading-review-title">复核与追问</h2>
                  <VerificationForm
                    readingId={readingId}
                    initialVerification={result.verification}
                  />
                  {canFollowUp ? <FollowUpForm readingId={readingId} /> : null}
                </div>
              </section>
            ) : null}
          </article>
          <ArchiveRail readingId={readingId} summary={summary} result={result} />
        </div>
      );
    }

    if (isZiweiNatal || isQizhengNatal) {
      const natalTitle = isZiweiNatal ? "紫微命盘" : "七政命盘";
      const natalIntro = isZiweiNatal
        ? "只展示已返回的十二宫与星曜事实。"
        : "只展示已返回的星体与宫位事实。";
      const natalViewModel = result.view_model;
      const natalViewReady =
        capabilityTier !== "C" &&
        showRuntimeChart &&
        natalViewModel != null &&
        (isZiweiNatal
          ? natalViewModel.schema_version === "ziwei-chart/v1"
          : natalViewModel.schema_version === "qizheng-chart/v1");
      const hasNatalContent = natalViewReady || result.accepted_copy != null;

      return (
        <div className={surface.readingLayout}>
          <article className={surface.readingBody} aria-label="解读正文">
            <header className={surface.readingHeader}>
              <ResultHeading>{natalTitle}</ResultHeading>
              <p>{natalIntro}</p>
            </header>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-workspace-title"
            >
              <div>
                <h2 id="reading-workspace-title">排盘结果</h2>
                {capabilityTier === "C" ? (
                  <Status
                    description="当前能力暂不可用，不会展示未确认的盘面或断法。"
                    state="unavailable"
                    title="结果服务暂时不可用，不会展示未确认内容"
                  />
                ) : !hasNatalContent ? (
                  <Status
                    description="服务端尚未返回可展示的盘面事实，不会伪造盘面。"
                    state="empty"
                    title="还没有可展示的盘面"
                  />
                ) : (
                  <>
                    {natalViewReady && natalViewModel ? (
                      <>
                        <EvidenceList
                          exactOnly
                          evidence={result.fact_panel?.evidence ?? []}
                          facts={result.fact_panel?.facts ?? []}
                        />
                        <RuntimeChart
                          viewModel={natalViewModel}
                          capability={result.capability}
                          timeLayerEntitlement={runtimeTimeLayerEntitlement}
                        />
                      </>
                    ) : null}
                    {result.accepted_copy ? (
                      <section aria-labelledby="reading-judgment-title">
                        <h2 id="reading-judgment-title">判断</h2>
                        <AcceptedCopy text={result.accepted_copy} />
                      </section>
                    ) : null}
                  </>
                )}
              </div>
            </section>

            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-note-title"
            >
              <div>
                <h2 id="reading-note-title">阅读说明</h2>
                <p className={surface.inlineNote}>
                  只提供已返回的盘面与确定性事实，不在页面编写判断。
                </p>
                <LimitNotice limits={result.fact_panel?.limits ?? null} />
              </div>
            </section>

            {isAccepted ? (
              <section
                className={surface.readingSection}
                data-layout="full-width-reading-section"
                aria-labelledby="reading-review-title"
              >
                <div>
                  <h2 id="reading-review-title">复核与追问</h2>
                  <VerificationForm
                    readingId={readingId}
                    initialVerification={result.verification}
                  />
                  {canFollowUp ? <FollowUpForm readingId={readingId} /> : null}
                </div>
              </section>
            ) : null}
          </article>
          <ArchiveRail readingId={readingId} summary={summary} result={result} />
        </div>
      );
    }

    return (
      <div className={surface.readingLayout}>
        <article className={surface.readingBody} aria-label="解读正文">
          <header className={surface.readingHeader}>
            <h2>{productId === "bazi-deep" ? "八字深度解读" : "八字命盘"}</h2>
            <p>
              {productId === "bazi-deep"
                ? "盘面事实与已接纳解读分开展示，便于逐项核对。"
                : "四柱、日主、月令、大运与已返回的盘面事实。"}
            </p>
          </header>

          {productId === "bazi-deep" ? (
            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-judgment-title"
            >
              <div>
                <h2 id="reading-judgment-title">深度解读</h2>
                <AcceptedCopy text={result.accepted_copy} />
              </div>
            </section>
          ) : null}

          <section
            className={surface.readingSection}
            data-layout="full-width-reading-section"
            aria-labelledby="reading-workspace-title"
          >
            <div>
              <h2 id="reading-workspace-title">排盘结果</h2>
              {capabilityTier === "C" ? (
                <Status
                  description="当前能力仍在适配中，暂不可用；未加载未确认的盘面或断法。"
                  state="unavailable"
                  title="结果服务暂时不可用，不会展示未确认内容"
                />
              ) : chart == null ? (
                <Status
                  description="服务端尚未返回可展示的四柱公开事实，不会伪造盘面。"
                  state="empty"
                  title="还没有可展示的盘面"
                />
              ) : (
                <>
                  <p className={surface.inlineNote}>
                    点击四柱可核对详细盘面；页面只展示系统已经计算并公开的事实。
                  </p>
                  <div data-bazi-chart-host="true">
                    <BaziChart
                      chart={chart}
                      title="八字命盘"
                      evidence={result.fact_panel?.evidence ?? []}
                      showInterpretiveSections={capabilityTier === "A"}
                      timeLayerEntitlement={timeLayerEntitlement}
                    />
                  </div>
                </>
              )}
            </div>
          </section>

          <section
            className={surface.readingSection}
            data-layout="full-width-reading-section"
            aria-labelledby="reading-note-title"
          >
            <div>
              <h2 id="reading-note-title">阅读说明</h2>
              {productId === "bazi-deep" ? (
                <p className={surface.inlineNote}>
                  深度解读只采用本次盘面与已接纳正文，不会把内部字段当作结论展示。
                </p>
              ) : baziDeepFulfilled ? (
                <p className={surface.inlineNote}>
                  专业深读已交付；免费盘面继续保留，本区不重复展示深读入口。
                </p>
              ) : (
                <p className={surface.inlineNote}>
                  当前是免费排盘预览，只提供命盘与确定性事实。完整深度解读待接入。
                </p>
              )}
              <LimitNotice limits={result.fact_panel?.limits ?? null} />
              {productId !== "bazi-deep" && !baziDeepFulfilled ? <BaziDeepEntry /> : null}
            </div>
          </section>

          {isAccepted ? (
            <section
              className={surface.readingSection}
              data-layout="full-width-reading-section"
              aria-labelledby="reading-review-title"
            >
              <div>
                <h2 id="reading-review-title">复核与追问</h2>
                <VerificationForm
                  readingId={readingId}
                  initialVerification={result.verification}
                />
                {canFollowUp ? <FollowUpForm readingId={readingId} /> : null}
              </div>
            </section>
          ) : null}
        </article>
        <ArchiveRail readingId={readingId} summary={summary} result={result} />
      </div>
    );
  }

  if (summary.status === "waiting_input") {
    return (
      <div className={surface.readingLayout}>
        <article className={surface.readingBody}>
          <NeedInputForm
            readingId={readingId}
            request={summary.input_request}
            onSubmitted={handleInputSubmitted}
          />
        </article>
        <ArchiveRail readingId={readingId} summary={summary} result={null} />
      </div>
    );
  }

  if (summary.status === "terminal_stopped") {
    return (
      <div className={surface.readingLayout}>
        <article className={surface.readingBody}>
          <Status
            actions={<Link href="/app">重新发起</Link>}
            description="服务端已停止本次解读，请重新发起。"
            state="error"
            title="本次解读已停止"
          />
        </article>
        <ArchiveRail readingId={readingId} summary={summary} result={null} />
      </div>
    );
  }

  const meta = statusMeta(summary.status);
  if (shouldKeepPolling(summary)) {
    return (
      <div className={surface.readingLayout}>
        <article className={surface.readingBody}>
          <WaitingStatus
            context={`${meta.text} 目标日期：${formatHorizon(summary.horizon)}`}
            elapsedMs={elapsedMs}
            onRestart={onRestart}
            onRetry={handleRetry}
          />
        </article>
        <ArchiveRail readingId={readingId} summary={summary} result={null} />
      </div>
    );
  }
  return (
    <div className={surface.readingLayout}>
      <article className={surface.readingBody}>
        <Status
          actions={
            summary.status === "runtime_unknown" ? (
              <button type="button" onClick={handleRetry}>
                重新检查状态
              </button>
            ) : null
          }
          description={`${meta.text} 目标日期：${formatHorizon(summary.horizon)}`}
          state={meta.tone === "error" ? "error" : "processing"}
          title={meta.label}
        />
      </article>
      <ArchiveRail readingId={readingId} summary={summary} result={null} />
    </div>
  );
}
