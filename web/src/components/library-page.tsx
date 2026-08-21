"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { ApiError, requestJson } from "@/lib/api/client";
import type { ContentPublicItem, ContentPublicResponse } from "@/lib/api/contracts";

import { PublicPageShell } from "./public-page-shell";
import styles from "./library-page.module.css";

function asItems(payload: ContentPublicItem | ContentPublicResponse): ContentPublicItem[] {
  const items = "items" in payload ? payload.items : [payload];
  return items.filter((item) => item.title || item.summary || item.body);
}

function slugFromKey(contentKey: string, prefix: string): string {
  return contentKey.startsWith(prefix) ? contentKey.slice(prefix.length) : contentKey;
}

function isMissingContent(reason: unknown): boolean {
  return reason instanceof ApiError && reason.status === 404;
}

function LibraryPageShell({ children }: { readonly children: ReactNode }) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <div className={styles.column}>
          <header className={styles.header}>
            <h1>知识内容</h1>
            <p>只展示已发布的文章。</p>
          </header>
          {children}
        </div>
      </main>
    </PublicPageShell>
  );
}

export function LibraryIndexView() {
  const [status, setStatus] = useState<"loading" | "empty" | "error" | "ready">("loading");
  const [items, setItems] = useState<ContentPublicItem[]>([]);
  const [draftQuery, setDraftQuery] = useState("");
  const [draftTopic, setDraftTopic] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [appliedTopic, setAppliedTopic] = useState("");

  const sourceUrl = (() => {
    const params = new URLSearchParams({
      prefix: "library",
      locale: "zh-CN",
      limit: "100",
    });
    if (appliedQuery) params.set("q", appliedQuery);
    if (appliedTopic) params.set("topic", appliedTopic);
    return `/api/v1/content?${params.toString()}`;
  })();

  useEffect(() => {
    let cancelled = false;
    void requestJson<ContentPublicItem | ContentPublicResponse>(sourceUrl)
      .then((payload) => {
        if (cancelled) return;
        const next = asItems(payload);
        setItems(next);
        setStatus(next.length ? "ready" : "empty");
      })
      .catch((reason) => {
        if (cancelled) return;
        setItems([]);
        setStatus(isMissingContent(reason) ? "empty" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  const filterOpen = status === "ready" || Boolean(appliedQuery || appliedTopic);

  function submitFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!filterOpen) return;
    setAppliedQuery(draftQuery.trim());
    setAppliedTopic(draftTopic);
  }

  return (
    <LibraryPageShell>
      {status === "loading" ? (
        <p className={styles.status} role="status">
          正在读取已发布内容。
        </p>
      ) : null}

      {status === "error" ? (
        <p className={styles.empty} role="alert">
          读取失败，请重试
        </p>
      ) : null}

      {status === "empty" && !filterOpen ? (
        <p className={styles.empty} role="status">
          还没有可展示的内容
        </p>
      ) : null}

      {filterOpen ? (
        <form aria-label="知识内容筛选" className={styles.filters} onSubmit={submitFilter} role="search">
          <label htmlFor="library-search">搜索内容</label>
          <input
            id="library-search"
            onChange={(event) => setDraftQuery(event.target.value)}
            type="search"
            value={draftQuery}
          />
          <label htmlFor="library-topic">按主题筛选</label>
          <select
            id="library-topic"
            onChange={(event) => setDraftTopic(event.target.value)}
            value={draftTopic}
          >
            <option value="">全部主题</option>
            <option value="术数基础">术数基础</option>
            <option value="现实核对">现实核对</option>
            <option value="方法与边界">方法与边界</option>
          </select>
          <button type="submit">筛选</button>
        </form>
      ) : null}

      {status === "empty" && filterOpen ? (
        <p className={styles.empty} role="status">
          没有匹配的公开内容
        </p>
      ) : null}

      {status === "ready" ? (
        <ul className={styles.list}>
          {items.map((item) => {
            const slug = slugFromKey(item.content_key, "library.");
            return (
              <li key={`${item.content_key}:${item.revision}`}>
                {item.title ? (
                  <Link href={`/library/${encodeURIComponent(slug)}`}>{item.title}</Link>
                ) : (
                  <Link href={`/library/${encodeURIComponent(slug)}`}>阅读</Link>
                )}
                {item.summary ? <p>{item.summary}</p> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </LibraryPageShell>
  );
}

export function LibraryArticleView({ slug }: { readonly slug: string }) {
  const [status, setStatus] = useState<"loading" | "empty" | "error" | "ready">("loading");
  const [item, setItem] = useState<ContentPublicItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    void requestJson<ContentPublicItem | ContentPublicResponse>(
      `/api/v1/content/${encodeURIComponent(`library.${slug}`)}`,
    )
      .then((payload) => {
        if (cancelled) return;
        const next = asItems(payload)[0] ?? null;
        setItem(next);
        setStatus(next ? "ready" : "empty");
      })
      .catch((reason) => {
        if (cancelled) return;
        setItem(null);
        setStatus(isMissingContent(reason) ? "empty" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (status === "loading") {
    return (
      <LibraryPageShell>
        <p className={styles.status} role="status">
          正在读取已发布内容。
        </p>
      </LibraryPageShell>
    );
  }

  if (status === "error") {
    return (
      <LibraryPageShell>
        <section role="alert">
          <p className={styles.empty}>读取失败，请重试</p>
          <form action="/library">
            <button className={styles.back} type="submit">
              返回知识内容
            </button>
          </form>
        </section>
      </LibraryPageShell>
    );
  }

  if (status === "empty" || item === null) {
    return (
      <LibraryPageShell>
        <section role="status">
          <p className={styles.empty}>没有可展示的文章</p>
          <form action="/library">
            <button className={styles.back} type="submit">
              返回知识内容
            </button>
          </form>
        </section>
      </LibraryPageShell>
    );
  }

  return (
    <LibraryPageShell>
      <article>
        {item.title ? <h2>{item.title}</h2> : null}
        {item.summary ? <p>{item.summary}</p> : null}
        {item.body ? <div>{item.body}</div> : null}
      </article>
    </LibraryPageShell>
  );
}
