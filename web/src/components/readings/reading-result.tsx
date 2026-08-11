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
  formatCapabilityIds,
  formatDimensionIds,
  formatHorizon,
  formatObjectId,
  splitAcceptedCopy,
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
import { VerificationForm } from "./verification-form";

import styles from "./reading-result.module.css";

const DEFAULT_POLL_MS = 2000;

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
  summary,
  result,
}: Readonly<{
  summary: ReadingVersionSummary;
  result: ReadingResultResponse | null;
}>) {
  const scope = result?.fact_panel?.request_view ?? null;
  const meta = statusMeta(summary.status);

  return (
    <aside className={surface.evidenceRail} aria-labelledby="reading-summary-title">
      <div className={surface.rail}>
        <h2 id="reading-summary-title">阅读档案</h2>
        <dl className={surface.railMeta}>
          <div>
            <dt>术法</dt>
            <dd>
              {scope
                ? formatCapabilityIds(scope.capability_ids)
                : formatCapabilityIds([summary.capability_id])}
            </dd>
          </div>
          <div>
            <dt>对象</dt>
            <dd>
              {scope
                ? formatObjectId(scope.object_id)
                : formatObjectId(summary.object_id)}
            </dd>
          </div>
          <div>
            <dt>主题</dt>
            <dd>
              {scope
                ? formatDimensionIds(scope.dimension_ids)
                : formatDimensionIds(summary.dimension_ids)}
            </dd>
          </div>
          <div>
            <dt>目标日期</dt>
            <dd>{formatHorizon(summary.horizon)}</dd>
          </div>
          <div>
            <dt>版本</dt>
            <dd>v{summary.version}</dd>
          </div>
        </dl>
        <p className={surface.railTagRow}>
          <span className={surface.stateTag} data-state={meta.tone}>
            {meta.label}
          </span>
        </p>
        <p className={surface.railNote}>
          只展示服务端公开摘要；状态与正文分开保存，现实反馈独立记录，不会回写盘面。
        </p>
      </div>
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

  if (loading || (summary?.status === "accepted" && !result)) {
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

  if (summary.status === "accepted" && result) {
    const isBazi = summary.capability_id === "bazi";
    const isFortune = summary.capability_id === "fortune";
    const isLiuyao = summary.capability_id === "liuyao";
    const publicFacts = result.fact_panel?.facts ?? [];
    const chart = buildBaziChartView(publicFacts);
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
    const copyParts = splitAcceptedCopy(result.accepted_copy);
    const question = result.fact_panel?.question ?? "本次解读";
    const scopeLabel = formatCapabilityIds([summary.capability_id]);

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

            {isLiuyao ? (
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

            <section
              className={surface.readingSection}
              aria-labelledby="reading-fact-title"
            >
              <span className={surface.sectionIndex} aria-hidden="true">
                {isLiuyao || hasFortuneTimeline ? "03" : "02"}
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
                {isLiuyao || hasFortuneTimeline ? "04" : "03"}
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

            <section
              className={surface.readingSection}
              aria-labelledby="reading-review-title"
            >
              <span className={surface.sectionIndex} aria-hidden="true">
                {isLiuyao || hasFortuneTimeline ? "05" : "04"}
              </span>
              <div>
                <h2 id="reading-review-title">复核与追问</h2>
                <VerificationForm
                  readingId={readingId}
                  facts={generalFactPanel?.facts ?? []}
                  initialVerification={result.verification}
                />
                <FollowUpForm readingId={readingId} />
              </div>
            </section>
          </article>
          <ArchiveRail summary={summary} result={result} />
        </div>
      );
    }

    return (
      <div className={surface.readingLayout}>
        <article className={surface.readingBody} aria-label="解读正文">
          <header className={surface.readingHeader}>
            <h2>{copyParts.headline ?? question}</h2>
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

          <section
            className={surface.readingSection}
            aria-labelledby="reading-workspace-title"
          >
            <span className={surface.sectionIndex} aria-hidden="true">
              02
            </span>
            <div>
              <h2 id="reading-workspace-title">盘面证据</h2>
              <p className={surface.inlineNote}>
                先看结论，再点开盘面核对服务端公开事实；前端不本地排盘。
              </p>
              <BaziChart chart={chart} title="八字命盘" />
            </div>
          </section>

          <section
            className={surface.readingSection}
            aria-labelledby="reading-fact-title"
          >
            <span className={surface.sectionIndex} aria-hidden="true">
              03
            </span>
            <div>
              <h2 id="reading-fact-title">事实</h2>
              <FactPanel panel={result.fact_panel} />
            </div>
          </section>

          <section
            className={surface.readingSection}
            aria-labelledby="reading-evidence-title"
          >
            <span className={surface.sectionIndex} aria-hidden="true">
              04
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

          <section
            className={surface.readingSection}
            aria-labelledby="reading-review-title"
          >
            <span className={surface.sectionIndex} aria-hidden="true">
              05
            </span>
            <div>
              <h2 id="reading-review-title">复核与追问</h2>
              <VerificationForm
                readingId={readingId}
                facts={result.fact_panel?.facts ?? []}
                initialVerification={result.verification}
              />
              <FollowUpForm readingId={readingId} />
            </div>
          </section>
        </article>
        <ArchiveRail summary={summary} result={result} />
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
        <ArchiveRail summary={summary} result={null} />
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
        <ArchiveRail summary={summary} result={null} />
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
      <ArchiveRail summary={summary} result={null} />
    </div>
  );
}
