"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  getReadingResult,
  pollReading,
  type ReadingResultResponse,
  type ReadingVersionSummary,
} from "@/lib/api";
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
import surface from "@/components/app-surface.module.css";

import { AcceptedCopy } from "./accepted-copy";
import { BaziChart } from "./bazi-chart";
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

import styles from "./reading-result.module.css";

const DEFAULT_POLL_MS = 2000;
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
        tone: "error",
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

        if (RESULT_READY_STATUSES.has(response.status)) {
          const nextResult = await getReadingResult(readingId);
          if (cancelled) return;
          setResult(nextResult);
          if (response.status === "accepted") return;
          schedule(DEFAULT_POLL_MS);
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

  if (error) {
    return (
      <article className={surface.readingBody}>
        <div className={styles.error} role="alert">
          <p className={styles.errorMessage}>{error}</p>
          <button
            type="button"
            className={styles.retryButton}
            onClick={handleRetry}
          >
            重试
          </button>
        </div>
      </article>
    );
  }

  if (
    loading ||
    (summary && RESULT_READY_STATUSES.has(summary.status) && !result)
  ) {
    return (
      <article className={surface.readingBody}>
        <div className={styles.statusCard} role="status">
          <h2 className={styles.statusLabel}>正在读取结果…</h2>
          <p className={styles.statusText}>
            页面只展示服务端公开摘要；状态与正文分开保存。
          </p>
        </div>
      </article>
    );
  }

  if (!summary) {
    return null;
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
    // A missing projection is C only for a route that actually depends on a
    // Runtime ViewModel. Plain legacy result pages do not have this gate.
    const requiresCapabilityProjection = isBazi || result.view_model != null;
    const capabilityTier =
      result.capability?.tier ?? (requiresCapabilityProjection ? "C" : null);
    const showRuntimeChart = capabilityTier === "A" || capabilityTier === "B";
    const isFortune = summary.capability_id === "fortune";
    const isLiuyao = summary.capability_id === "liuyao";
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

    if (!isBazi) {
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
                  <RuntimeChart viewModel={result.view_model} capability={result.capability} />
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
                <p className={surface.inlineNote} data-capability-tier="C">
                  当前能力仍在适配中，暂不可用；未加载未确认的盘面或断法。
                </p>
              ) : (
                <>
                  <p className={surface.inlineNote}>
                    点击四柱可核对详细盘面；页面只展示系统已经计算并公开的事实。
                  </p>
                  <BaziChart
                    chart={chart!}
                    title="八字命盘"
                    evidence={result.fact_panel?.evidence ?? []}
                    showInterpretiveSections={capabilityTier === "A"}
                  />
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
              ) : (
                <p className={surface.inlineNote}>
                  当前是免费排盘预览，只提供命盘与确定性事实，尚未生成完整深度解读。
                </p>
              )}
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
        </article>
        <ArchiveRail readingId={readingId} summary={summary} result={null} />
      </div>
    );
  }

  const meta = statusMeta(summary.status);
  return (
    <div className={surface.readingLayout}>
      <article className={surface.readingBody}>
        <div className={styles.statusCard} role="status">
          <h2 className={styles.statusLabel}>{meta.label}</h2>
          <p className={styles.statusText}>{meta.text}</p>
          <p className={styles.horizon}>
            目标日期：{formatHorizon(summary.horizon)}
          </p>
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
      </article>
      <ArchiveRail readingId={readingId} summary={summary} result={null} />
    </div>
  );
}
