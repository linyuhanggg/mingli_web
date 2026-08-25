"use client";

import Link from "next/link";

import { Status } from "@/components/ui/status";
import type { ZiweiChartViewModel } from "@/view-models/registry";

import styles from "./ziwei-free-summary.module.css";

export type ZiweiS4Offer = {
  name: string;
  coverage: string;
  priceText: string;
  refundBoundary: string;
};

export type ZiweiS4Phase = "entry" | "confirming" | "locked" | "gateway_unavailable";

export type ZiweiFreeSummaryProps = {
  view: ZiweiChartViewModel;
  offer?: ZiweiS4Offer | null;
  s4Phase?: ZiweiS4Phase;
};

const SKU_COPY = "按这张已排出的命盘宫位与四化逐项核验，不另作裁决。";

function lifePalace(view: ZiweiChartViewModel) {
  return view.palaces.find((item) => item.palace_id === view.life_palace_id);
}

function lifeMajorStars(view: ZiweiChartViewModel): readonly string[] {
  return (lifePalace(view)?.major_stars ?? []).filter((name) => name.trim().length > 0);
}

function summaryClauses(view: ZiweiChartViewModel): readonly string[] {
  const clauses: string[] = [];
  const stars = lifeMajorStars(view);
  if (stars.length) clauses.push(`命宫主星 ${stars.join("、")}`);
  const wuXing = view.core_facts?.five_elements_class?.trim();
  if (wuXing) clauses.push(wuXing);
  const limits = view.core_facts?.major_limits;
  if (limits?.length) clauses.push(`大限 ${limits.length} 步已列`);
  return clauses;
}

function sampleQuotes(view: ZiweiChartViewModel): readonly string[] {
  const quotes: string[] = [];
  const palace = lifePalace(view);
  const stars = lifeMajorStars(view);
  if (palace?.label && stars.length) quotes.push(`${palace.label} ${stars.join("、")}`);
  const hua = view.core_facts?.transformations?.find(
    (item) => item.star.trim() && item.transformation.trim(),
  );
  if (hua) quotes.push(`${hua.star} ${hua.transformation}`);
  return quotes;
}

function DeepReadEntry({
  offer,
  s4Phase,
  quotes,
}: Readonly<{
  offer?: ZiweiS4Offer | null;
  s4Phase?: ZiweiS4Phase;
  quotes: readonly string[];
}>) {
  if (s4Phase === "confirming") {
    return (
      <section className={styles.panel} id="ziwei-s4-deep" aria-labelledby="ziwei-s4-deep-title">
        <h2 className={styles.title} id="ziwei-s4-deep-title">
          深读
        </h2>
        <Status state="processing" title="确认中" description="正在等待服务端支付事实，不回显任何编号。" />
      </section>
    );
  }

  if (s4Phase === "locked") {
    return (
      <section className={styles.panel} id="ziwei-s4-deep" aria-labelledby="ziwei-s4-deep-title">
        <h2 className={styles.title} id="ziwei-s4-deep-title">
          深读
        </h2>
        <Status state="locked" />
      </section>
    );
  }

  if (s4Phase === "gateway_unavailable") {
    return (
      <section className={styles.panel} id="ziwei-s4-deep" aria-labelledby="ziwei-s4-deep-title">
        <h2 className={styles.title} id="ziwei-s4-deep-title">
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
    <section className={styles.panel} id="ziwei-s4-deep" aria-labelledby="ziwei-s4-deep-title">
      <h2 className={styles.title} id="ziwei-s4-deep-title">
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
          <p className={styles.note}>绑定当前这张已排出的命盘</p>
          <Link className={styles.loginLink} href="/auth/login">
            登录后继续
          </Link>
        </div>
      ) : (
        <Status
          state="unavailable"
          title="测试期未开放"
          description="当前没有可购买的命盘深读，不会显示价格，也不会发起结账。"
        />
      )}
    </section>
  );
}

export function ZiweiFreeSummary({
  view,
  offer = null,
  s4Phase = "entry",
}: ZiweiFreeSummaryProps) {
  const clauses = summaryClauses(view);
  const quotes = sampleQuotes(view);
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
