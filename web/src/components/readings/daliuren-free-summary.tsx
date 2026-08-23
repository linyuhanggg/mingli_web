"use client";

import Link from "next/link";

import { Status } from "@/components/ui/status";
import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-free-summary.module.css";

type Lesson = DaliurenChartViewModel["lessons"][number];
type Transmission = DaliurenChartViewModel["transmissions"][number];
type Patterns = NonNullable<NonNullable<DaliurenChartViewModel["core_facts"]>["structural_patterns"]>;

export type DaliurenS4Offer = {
  name: string;
  coverage: string;
  priceText: string;
  refundBoundary: string;
};

export type DaliurenS4Phase = "entry" | "confirming" | "locked" | "gateway_unavailable";

export type DaliurenFreeSummaryProps = {
  lessons: DaliurenChartViewModel["lessons"] | readonly Lesson[];
  transmissions: DaliurenChartViewModel["transmissions"] | readonly Transmission[];
  structuralPatterns?: Patterns | null;
  offer?: DaliurenS4Offer | null;
  s4Phase?: DaliurenS4Phase;
};

const SKU_COPY = "按这张已排出的课传与课体逐项核验，不另作裁决。";

function trimmed(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function lessonPairs(lessons: readonly Lesson[]): readonly string[] {
  const parts: string[] = [];
  for (const lesson of lessons) {
    const upper = trimmed(lesson.upper);
    const lower = trimmed(lesson.lower);
    if (!upper && !lower) continue;
    parts.push(upper && lower ? `${upper}/${lower}` : (upper ?? lower ?? ""));
  }
  return parts;
}

function transmissionPairs(transmissions: readonly Transmission[]): readonly string[] {
  const parts: string[] = [];
  for (const item of transmissions) {
    const branch = trimmed(item.branch);
    const general = trimmed(item.general);
    if (!branch && !general) continue;
    parts.push([branch, general].filter(Boolean).join(""));
  }
  return parts;
}

function patternNames(patterns: Patterns | null | undefined): readonly string[] {
  if (!patterns?.length) return [];
  return patterns.filter((item): item is string => typeof item === "string" && Boolean(item.trim())).map((item) => item.trim());
}

function summaryClauses(
  lessons: readonly Lesson[],
  transmissions: readonly Transmission[],
  patterns: Patterns | null | undefined,
): readonly string[] {
  const clauses: string[] = [];
  const lessonsText = lessonPairs(lessons);
  if (lessonsText.length) clauses.push(`四课 ${lessonsText.join("、")}`);
  const txText = transmissionPairs(transmissions);
  if (txText.length) clauses.push(`三传 ${txText.join("、")}`);
  const names = patternNames(patterns);
  if (names.length) clauses.push(`课体 ${names.join("、")}`);
  return clauses;
}

function sampleQuotes(
  lessons: readonly Lesson[],
  transmissions: readonly Transmission[],
  patterns: Patterns | null | undefined,
): readonly string[] {
  const quotes: string[] = [];
  for (const lesson of lessons) {
    const name = trimmed(lesson.lesson_id);
    if (name) quotes.push(name);
    const upper = trimmed(lesson.upper);
    if (upper) quotes.push(upper);
    const lower = trimmed(lesson.lower);
    if (lower) quotes.push(lower);
  }
  for (const item of transmissions) {
    const branch = trimmed(item.branch);
    if (branch) quotes.push(branch);
    const general = trimmed(item.general);
    if (general) quotes.push(general);
  }
  quotes.push(...patternNames(patterns));
  return [...new Set(quotes)];
}

function DeepReadEntry({
  offer,
  s4Phase,
  quotes,
}: Readonly<{
  offer?: DaliurenS4Offer | null;
  s4Phase?: DaliurenS4Phase;
  quotes: readonly string[];
}>) {
  if (s4Phase === "confirming") {
    return (
      <section className={styles.panel} id="daliuren-s4-deep" aria-labelledby="daliuren-s4-deep-title">
        <h2 className={styles.title} id="daliuren-s4-deep-title">
          深读
        </h2>
        <Status state="processing" title="确认中" description="正在等待服务端支付事实，不回显任何编号。" />
      </section>
    );
  }

  if (s4Phase === "locked") {
    return (
      <section className={styles.panel} id="daliuren-s4-deep" aria-labelledby="daliuren-s4-deep-title">
        <h2 className={styles.title} id="daliuren-s4-deep-title">
          深读
        </h2>
        <Status state="locked" />
      </section>
    );
  }

  if (s4Phase === "gateway_unavailable") {
    return (
      <section className={styles.panel} id="daliuren-s4-deep" aria-labelledby="daliuren-s4-deep-title">
        <h2 className={styles.title} id="daliuren-s4-deep-title">
          深读
        </h2>
        <Status
          state="unavailable"
          title="支付暂时不可用"
          description="当前 Fake/不可用适配器不会被当成成功付款，也不会发起结账。"
        />
      </section>
    );
  }

  return (
    <section className={styles.panel} id="daliuren-s4-deep" aria-labelledby="daliuren-s4-deep-title">
      <h2 className={styles.title} id="daliuren-s4-deep-title">
        深读
      </h2>
      <p className={styles.skuCopy}>{SKU_COPY}</p>
      {quotes.length ? (
        <div>
          <p className={styles.kicker}>样例引用（已上屏事实）</p>
          <ul className={styles.quoteList}>
            {quotes.map((quote) => (
              <li key={quote}>
                <blockquote className={styles.quote}>{quote}</blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {offer ? (
        <div className={styles.offerCard}>
          <p className={styles.offerName}>{offer.name}</p>
          <p>{offer.coverage}</p>
          <p>{offer.priceText}</p>
          <p className={styles.note}>{offer.refundBoundary}</p>
          <p className={styles.note}>绑定当前这张已排出的课盘</p>
          <Link className={styles.loginLink} href="/auth/login">
            登录后继续
          </Link>
        </div>
      ) : (
        <Status
          state="unavailable"
          title="测试期未开放"
          description="当前没有可购买的课盘深读，不会显示价格，也不会发起结账。"
        />
      )}
    </section>
  );
}

export function DaliurenFreeSummary({
  lessons,
  transmissions,
  structuralPatterns = null,
  offer = null,
  s4Phase = "entry",
}: DaliurenFreeSummaryProps) {
  const clauses = summaryClauses(lessons, transmissions, structuralPatterns);
  const quotes = sampleQuotes(lessons, transmissions, structuralPatterns);
  return (
    <>
      {clauses.length ? (
        <section className={styles.panel} aria-label="基础摘要">
          <h2 className={styles.title}>基础摘要</h2>
          <p className={styles.summary}>{`${clauses.join("；")}。`}</p>
        </section>
      ) : null}
      <DeepReadEntry offer={offer} quotes={quotes} s4Phase={s4Phase} />
    </>
  );
}
