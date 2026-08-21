"use client";

import { useEffect, useState } from "react";

import { ApiError, requestJson } from "@/lib/api/client";
import type { ContentPublicItem, ContentPublicResponse } from "@/lib/api/contracts";

import { PublicPageShell } from "./public-page-shell";
import styles from "./daily-page.module.css";

type DailyState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error" }
  | { status: "ready"; items: ContentPublicItem[] };

function isMissingContent(reason: unknown): boolean {
  return reason instanceof ApiError && reason.status === 404;
}

function asItems(payload: ContentPublicItem | ContentPublicResponse): ContentPublicItem[] {
  const items = "items" in payload ? payload.items : [payload];
  return items.filter((item) => item.title || item.summary || item.body);
}

export function DailyPageView() {
  const [state, setState] = useState<DailyState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    void requestJson<ContentPublicItem | ContentPublicResponse>("/api/v1/content/daily")
      .then((payload) => {
        if (cancelled) return;
        const items = asItems(payload);
        setState(items.length ? { status: "ready", items } : { status: "empty" });
      })
      .catch((reason) => {
        if (cancelled) return;
        setState(isMissingContent(reason) ? { status: "empty" } : { status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <div className={styles.column}>
          <header className={styles.header}>
            <h1>每日</h1>
            <p>只展示当天已发布的内容</p>
          </header>

          {state.status === "loading" ? (
            <p className={styles.status} role="status">
              正在读取今日内容…
            </p>
          ) : null}

          {state.status === "error" ? (
            <p className={styles.empty} role="alert">
              读取失败，请重试
            </p>
          ) : null}

          {state.status === "empty" ? (
            <p className={styles.empty} role="status">
              今日还没有可展示的内容
            </p>
          ) : null}

          {state.status === "ready" ? (
            <ul className={styles.list}>
              {state.items.map((item, index) => (
                <li className={styles.item} key={`${item.revision}:${index}`}>
                  {item.title ? <h2>{item.title}</h2> : null}
                  {item.summary ? <p className={styles.summary}>{item.summary}</p> : null}
                  {item.body ? <div className={styles.body}>{item.body}</div> : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </main>
    </PublicPageShell>
  );
}
