"use client";

import Link from "next/link";

import { Status } from "@/components/ui/status";

import styles from "./bazi-deep-entry.module.css";

export type BaziS4Offer = {
  name: string;
  coverage: string;
  priceText: string;
  refundBoundary: string;
};

export type BaziS4Phase = "entry" | "confirming" | "locked" | "gateway_unavailable";

export type BaziDeepEntryProps = {
  quotes?: readonly string[];
  offer?: BaziS4Offer | null;
  s4Phase?: BaziS4Phase;
};

const SKU_COPY = "按这张已排出的四柱与月令逐项核验，不另作裁决。";

export function BaziDeepEntry({
  quotes = [],
  offer = null,
  s4Phase = "entry",
}: BaziDeepEntryProps) {
  if (s4Phase === "confirming") {
    return (
      <section className={styles.panel} id="bazi-s4-deep" aria-labelledby="bazi-s4-deep-title">
        <h2 className={styles.title} id="bazi-s4-deep-title">
          深读
        </h2>
        <Status state="processing" title="确认中" description="正在等待服务端支付事实，不回显任何编号。" />
      </section>
    );
  }

  if (s4Phase === "locked") {
    return (
      <section className={styles.panel} id="bazi-s4-deep" aria-labelledby="bazi-s4-deep-title">
        <h2 className={styles.title} id="bazi-s4-deep-title">
          深读
        </h2>
        <Status state="locked" />
      </section>
    );
  }

  if (s4Phase === "gateway_unavailable") {
    return (
      <section className={styles.panel} id="bazi-s4-deep" aria-labelledby="bazi-s4-deep-title">
        <h2 className={styles.title} id="bazi-s4-deep-title">
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
    <section className={styles.panel} id="bazi-s4-deep" aria-labelledby="bazi-s4-deep-title">
      <h2 className={styles.title} id="bazi-s4-deep-title">
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
