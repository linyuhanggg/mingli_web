"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { requestJson } from "@/lib/api/client";
import type { ContentPublicItem, ContentPublicResponse } from "@/lib/api/contracts";
import type { PublicContentSource, PublicContentSurfaceSpec } from "@/lib/secondary-surfaces";

import { SecondaryStatus } from "./secondary-status";
import { SecondarySurfaceFrame } from "./secondary-surface-frame";
import styles from "./secondary-surfaces.module.css";

type PublicContentSurfaceProps = {
  readonly surface: PublicContentSurfaceSpec;
  readonly contentSource?: PublicContentSource;
};

type ProjectionPayload = ContentPublicItem | ContentPublicResponse;

type ProjectionRequestState = {
  readonly sourceUrl: string;
  readonly status: "ready" | "error";
  readonly projection: ProjectionPayload | null;
};

function projectionItems(
  projection: ProjectionPayload | null,
): ContentPublicItem[] {
  if (!projection) return [];
  return "items" in projection ? projection.items : [projection];
}

export function PublicContentSurface({ surface, contentSource }: PublicContentSurfaceProps) {
  const [projectionRequest, setProjectionRequest] = useState<ProjectionRequestState | null>(null);
  const [filterDraftQuery, setFilterDraftQuery] = useState("");
  const [filterDraftTopic, setFilterDraftTopic] = useState("");
  const [appliedFilterQuery, setAppliedFilterQuery] = useState("");
  const [appliedFilterTopic, setAppliedFilterTopic] = useState("");
  const sourceUrl = (() => {
    if (!contentSource) return null;
    if (contentSource.kind === "item") {
      return `/api/v1/content/${encodeURIComponent(contentSource.contentKey)}`;
    }
    const params = new URLSearchParams({
      prefix: contentSource.prefix,
      locale: "zh-CN",
      limit: "100",
    });
    if (appliedFilterQuery) params.set("q", appliedFilterQuery);
    if (appliedFilterTopic) params.set("topic", appliedFilterTopic);
    return `/api/v1/content?${params.toString()}`;
  })();

  useEffect(() => {
    if (!sourceUrl) return;
    let cancelled = false;
    void requestJson<ProjectionPayload>(sourceUrl)
      .then((response) => {
        if (!cancelled) {
          setProjectionRequest({ sourceUrl, status: "ready", projection: response });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProjectionRequest({ sourceUrl, status: "error", projection: null });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  const projection = projectionRequest?.sourceUrl === sourceUrl
    ? projectionRequest.projection
    : null;
  const projectionState = !sourceUrl
    ? "idle"
    : projectionRequest?.sourceUrl === sourceUrl
      ? projectionRequest.status
      : "loading";
  const items = projectionItems(projection);
  const hasPublishedContent = items.length > 0;
  const filterEnabled = contentSource?.kind === "index" && projectionState === "ready";
  const filterApplied = Boolean(appliedFilterQuery || appliedFilterTopic);
  const hasFilteredEmptyResult = filterEnabled && filterApplied && !hasPublishedContent;
  const title = hasPublishedContent && contentSource?.kind === "item"
    ? surface.projectionTitle ?? surface.title
    : surface.title;
  const intro = hasPublishedContent && contentSource?.kind === "item"
    ? surface.projectionIntro ?? "以下内容来自已发布的 CMS 投影。"
    : surface.intro;

  return (
    <SecondarySurfaceFrame eyebrow={surface.eyebrow} intro={intro} title={title}>
      {surface.entries ? (
        <nav aria-label="工具入口">
          <ul className={styles.entryGrid}>
            {surface.entries.map((entry) => (
              <li key={entry.href}>
                <Link href={entry.href}>
                  <span className={styles.entryHeading}>
                    <strong>{entry.title}</strong>
                    <small>{entry.status}</small>
                  </span>
                  <span>{entry.description}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}

      {surface.sections?.length ? (
        <div className={styles.sectionGrid}>
          {surface.sections.map((section) => (
            <section className={styles.section} key={section.title}>
              <h2>{section.title}</h2>
              <p>{section.description}</p>
              {section.items?.length ? (
                <ul>
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>
      ) : null}

      {surface.contentFilters ? (
        <form
          aria-describedby="content-filters-disabled-reason"
          aria-label="知识内容筛选"
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedFilterQuery(filterDraftQuery.trim());
            setAppliedFilterTopic(filterDraftTopic);
          }}
          role="search"
        >
          <fieldset className={styles.filterFieldset} disabled={!filterEnabled}>
            <legend className={styles.filterLegend}>内容索引筛选</legend>
            <div className={styles.fields}>
              <div className={styles.field}>
                <label htmlFor="content-search">{surface.contentFilters.searchLabel}</label>
                <input
                  id="content-search"
                  name="query"
                  onChange={(event) => setFilterDraftQuery(event.target.value)}
                  type="search"
                  value={filterDraftQuery}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="content-topic">{surface.contentFilters.topicLabel}</label>
                <select
                  id="content-topic"
                  name="topic"
                  onChange={(event) => setFilterDraftTopic(event.target.value)}
                  value={filterDraftTopic}
                >
                  {surface.contentFilters.topics.map((topic) => (
                    <option key={topic} value={topic === "全部主题" ? "" : topic}>
                      {topic}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button disabled={!filterEnabled} type="submit">
              筛选
            </button>
          </fieldset>
          <p className={styles.disabledReason} id="content-filters-disabled-reason">
            {filterEnabled ? "筛选只查询已发布内容。" : surface.contentFilters.disabledReason}
          </p>
        </form>
      ) : null}

      {hasPublishedContent ? (
        <section aria-labelledby="published-content-heading" className={styles.section}>
          <h2 id="published-content-heading">{surface.projectionHeading ?? "已发布内容"}</h2>
          <ul>
            {items.map((item) => {
              const href = contentSource?.kind === "index" && contentSource.hrefBase
                ? `${contentSource.hrefBase}/${encodeURIComponent(
                    item.content_key.startsWith(contentSource.prefix)
                      ? item.content_key.slice(contentSource.prefix.length)
                      : item.content_key,
                  )}`
                : null;
              return (
                <li key={`${item.content_key}:${item.revision}`}>
                  {item.title ? <strong>{item.title}</strong> : null}
                  {href ? (
                    <Link href={href}>阅读 {item.content_key}</Link>
                  ) : (
                    <strong>{item.content_key}</strong>
                  )}
                  {item.summary ? <p>{item.summary}</p> : null}
                  {item.topic ? <p>{item.topic}</p> : null}
                  {item.source_title ? (
                    item.source_url ? (
                      <p>
                        <Link href={item.source_url}>{item.source_title}</Link>
                      </p>
                    ) : (
                      <p>来源：{item.source_title}</p>
                    )
                  ) : null}
                  <p className={styles.publishedBody}>{item.body}</p>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {surface.form ? (
        <form
          aria-describedby="tool-form-disabled-reason"
          aria-label={`${surface.title}输入`}
          className={styles.form}
        >
          <div className={styles.fields}>
            {surface.form.fields.map((field) => {
              const hintId = `${field.id}-hint`;
              return (
                <div className={styles.field} key={field.id}>
                  <label htmlFor={field.id}>{field.label}</label>
                  {field.type === "textarea" ? (
                    <textarea
                      aria-describedby={hintId}
                      aria-readonly="true"
                      id={field.id}
                      name={field.id}
                      readOnly
                      rows={4}
                    />
                  ) : (
                    <input
                      aria-describedby={hintId}
                      aria-readonly="true"
                      id={field.id}
                      name={field.id}
                      readOnly
                      type="text"
                    />
                  )}
                  <p id={hintId}>{field.hint}</p>
                </div>
              );
            })}
          </div>
          <button disabled type="submit">
            {surface.form.submitLabel}
          </button>
          <p className={styles.disabledReason} id="tool-form-disabled-reason">
            {surface.form.disabledReason}
          </p>
        </form>
      ) : null}

      {hasPublishedContent || hasFilteredEmptyResult || projectionState === "loading" ? null : (
        <SecondaryStatus
          action={surface.action}
          description={surface.statusDescription}
          state={surface.state}
          title={surface.statusTitle}
        />
      )}
      {hasFilteredEmptyResult ? (
        <SecondaryStatus
          description="换一个关键词或主题；页面只搜索已经发布的内容。"
          state="empty"
          title="没有匹配的公开内容"
        />
      ) : null}
    </SecondarySurfaceFrame>
  );
}
