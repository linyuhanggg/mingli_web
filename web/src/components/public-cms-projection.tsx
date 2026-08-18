"use client";

import { useEffect, useId, useState } from "react";

import { requestJson } from "@/lib/api/client";
import type { ContentPublicItem, ContentPublicResponse } from "@/lib/api/contracts";

import { StatusPanel } from "./status-panel";
import styles from "./editorial-page.module.css";

export type PublicCmsSource =
  | { readonly kind: "item"; readonly contentKey: string }
  | { readonly kind: "index"; readonly prefix: string };

type PublicCmsProjectionProps = {
  readonly heading: string;
  readonly source: PublicCmsSource;
  /**
   * 内容页需要如实显示 loading/empty/error 状态面板。
   * 首页这类以行动收尾的版面不需要——投影照常请求，没有内容时整块不渲染。
   */
  readonly silentWhenUnavailable?: boolean;
};

type ProjectionPayload = ContentPublicItem | ContentPublicResponse;
type ProjectionState = "loading" | "ready" | "empty" | "error";
type ProjectionResult = {
  readonly sourceUrl: string;
  readonly state: Exclude<ProjectionState, "loading">;
  readonly items: ContentPublicItem[];
};

function itemsFromPayload(payload: ProjectionPayload): ContentPublicItem[] {
  return "items" in payload ? payload.items : [payload];
}

function isNotFound(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    (error as { status?: unknown }).status === 404
  );
}

export function PublicCmsProjection({ heading, source, silentWhenUnavailable = false }: PublicCmsProjectionProps) {
  const headingId = useId();
  const [result, setResult] = useState<ProjectionResult | null>(null);
  const sourceUrl = (() => {
    if (source.kind === "item") {
      return `/api/v1/content/${encodeURIComponent(source.contentKey)}`;
    }
    const params = new URLSearchParams({
      prefix: source.prefix,
      locale: "zh-CN",
      limit: "100",
    });
    return `/api/v1/content?${params.toString()}`;
  })();

  useEffect(() => {
    let cancelled = false;
    void requestJson<ProjectionPayload>(sourceUrl)
      .then((payload) => {
        if (cancelled) return;
        const nextItems = itemsFromPayload(payload);
        setResult({
          sourceUrl,
          state: nextItems.length > 0 ? "ready" : "empty",
          items: nextItems,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setResult({
          sourceUrl,
          state: isNotFound(error) ? "empty" : "error",
          items: [],
        });
      });
    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  const currentResult = result?.sourceUrl === sourceUrl ? result : null;
  const state: ProjectionState = currentResult?.state ?? "loading";
  const items = currentResult?.items ?? [];

  if (state !== "ready") {
    if (silentWhenUnavailable) return null;
    return (
      <StatusPanel
        description={
          state === "loading"
            ? "正在读取已发布 CMS 内容。"
            : state === "empty"
              ? "当前没有可公开的已发布内容；页面保留既有产品说明。"
              : "公开内容服务暂不可用；页面保留既有产品说明，不伪造动态内容。"
        }
        state={state === "loading" ? "loading" : state === "empty" ? "empty" : "disabled"}
        title={
          state === "loading"
            ? "正在读取已发布内容"
            : state === "empty"
              ? "没有已发布的 CMS 内容"
              : "CMS 内容暂不可用"
        }
      />
    );
  }

  return (
    <section aria-labelledby={headingId} className={styles.cmsProjection}>
      <h2 id={headingId}>{heading}</h2>
      <div className={styles.cmsProjectionList}>
        {items.map((item) => (
          <article className={styles.cmsProjectionItem} key={`${item.content_key}:${item.revision}`}>
            {item.title ? <h3>{item.title}</h3> : null}
            {item.summary ? <p className={styles.cmsProjectionSummary}>{item.summary}</p> : null}
            {item.topic ? <p className={styles.cmsProjectionTopic}>{item.topic}</p> : null}
            {item.source_title ? (
              item.source_url ? (
                <p className={styles.cmsProjectionSource}>
                  <a href={item.source_url}>{item.source_title}</a>
                </p>
              ) : (
                <p className={styles.cmsProjectionSource}>来源：{item.source_title}</p>
              )
            ) : null}
            <p className={styles.cmsProjectionBody}>{item.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
