"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminContentHistoryResponse,
  AdminContentIndexItem,
  AdminContentIndexResponse,
  AdminContentState,
  AdminContentRevision,
} from "@/lib/admin-content";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "contentKey", header: "内容", sortable: true },
  { key: "title", header: "标题", sortable: true },
  { key: "topic", header: "主题", sortable: true },
  { key: "revision", header: "版本", sortable: true },
  { key: "state", header: "发布态", sortable: true },
  { key: "author", header: "责任人", sortable: true },
  { key: "updatedAt", header: "更新时间", sortable: true },
];

const STATE_COPY: Record<AdminContentState, string> = {
  draft: "草稿",
  preview: "预览",
  scheduled: "已排期",
  published: "已发布",
  withdrawn: "已撤回",
  archived: "已归档",
};

const PAGE_CONTENT_KEY_PREFIXES = ["home.", "page.", "notice.", "seo."] as const;

function matchesContentScope(value: string, prefix: string): boolean {
  return prefix.endsWith(".")
    ? value.startsWith(prefix)
    : value === prefix || value.startsWith(`${prefix}.`);
}

function isRegisteredPageContentKey(value: string): boolean {
  return value === "notice" || PAGE_CONTENT_KEY_PREFIXES.some((prefix) => matchesContentScope(value, prefix));
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function contentIndexUrl(prefix?: string): string {
  const params = new URLSearchParams();
  if (prefix) params.set("prefix", prefix);
  params.set("locale", "zh-CN");
  params.set("limit", "100");
  return `/api/v1/admin/cms?${params.toString()}`;
}

async function fetchContentIndex(
  prefix: string | undefined,
  prefixes: readonly string[] | undefined,
): Promise<
  | { ok: true; data: AdminContentIndexResponse }
  | { ok: false; status: number; title: string }
> {
  const filters = prefixes?.length ? prefixes : [prefix];
  const responses = await Promise.all(
    filters.map((filter) => adminFetch<AdminContentIndexResponse>(contentIndexUrl(filter))),
  );
  const failure = responses.find((response) => !response.ok);
  if (failure) return failure;

  const latestByKey = new Map<string, AdminContentIndexItem>();
  for (const response of responses) {
    if (!response.ok) continue;
    for (const revision of response.data.revisions) {
      const key = `${revision.content_key}\u0000${revision.locale}`;
      const current = latestByKey.get(key);
      if (!current || revision.revision > current.revision) {
        latestByKey.set(key, revision);
      }
    }
  }
  return {
    ok: true,
    data: {
      revisions: [...latestByKey.values()].sort((left, right) =>
        left.content_key.localeCompare(right.content_key),
      ),
    },
  };
}

export function AdminCmsSurface({
  title,
  prefix,
  prefixes,
  role,
}: {
  title: string;
  prefix?: string;
  prefixes?: readonly string[];
  role?: StaffRole;
}) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const prefixScopeKey = prefixes?.join("\u0000") ?? "";
  const contentPrefixes = prefixScopeKey ? prefixScopeKey.split("\u0000") : undefined;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminContentIndexResponse>({ revisions: [] });
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [historyState, setHistoryState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [history, setHistory] = useState<AdminContentHistoryResponse>({ revisions: [] });
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [activeRevisionId, setActiveRevisionId] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState("");
  const [summaryDraft, setSummaryDraft] = useState("");
  const [topicDraft, setTopicDraft] = useState("");
  const [sourceTitleDraft, setSourceTitleDraft] = useState("");
  const [sourceUrlDraft, setSourceUrlDraft] = useState("");
  const [bodyDraft, setBodyDraft] = useState("");
  const [reason, setReason] = useState("");
  const [scheduleAt, setScheduleAt] = useState("");
  const [commandState, setCommandState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [commandError, setCommandError] = useState<string | null>(null);
  const [createKeyDraft, setCreateKeyDraft] = useState("");
  const [createTitleDraft, setCreateTitleDraft] = useState("");
  const [createSummaryDraft, setCreateSummaryDraft] = useState("");
  const [createTopicDraft, setCreateTopicDraft] = useState("");
  const [createSourceTitleDraft, setCreateSourceTitleDraft] = useState("");
  const [createSourceUrlDraft, setCreateSourceUrlDraft] = useState("");
  const [createBodyDraft, setCreateBodyDraft] = useState("");
  const [createReason, setCreateReason] = useState("");
  const [createState, setCreateState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await fetchContentIndex(
        prefix,
        prefixScopeKey ? prefixScopeKey.split("\u0000") : undefined,
      );
      if (cancelled) return;
      if (!response.ok) {
        setState(
          response.status === 403
            ? "forbidden"
            : response.status === 0 || response.status >= 500
              ? "unavailable"
              : "error",
        );
        setError(response.title);
        return;
      }
      setData(response.data);
      setState(response.data.revisions.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, [prefix, prefixScopeKey]);

  async function openHistory(contentKey: string) {
    setSelectedKey(contentKey);
    setHistoryState("loading");
    setHistoryError(null);
    const response = await adminFetch<AdminContentHistoryResponse>(
      `/api/v1/admin/cms/${encodeURIComponent(contentKey)}/history?locale=zh-CN`,
    );
    if (!response.ok) {
      setHistoryState("error");
      setHistoryError(response.title);
      return;
    }
    setHistory(response.data);
    const firstRevision = response.data.revisions[0];
    setActiveRevisionId(firstRevision?.revision_id ?? null);
    setTitleDraft(firstRevision?.title ?? "");
    setSummaryDraft(firstRevision?.summary ?? "");
    setTopicDraft(firstRevision?.topic ?? "");
    setSourceTitleDraft(firstRevision?.source_title ?? "");
    setSourceUrlDraft(firstRevision?.source_url ?? "");
    setBodyDraft(firstRevision?.body ?? "");
    setReason("");
    setScheduleAt("");
    setCommandState("idle");
    setCommandError(null);
    setHistoryState("ready");
  }

  function selectRevision(revision: AdminContentHistoryResponse["revisions"][number]) {
    setActiveRevisionId(revision.revision_id);
    setTitleDraft(revision.title ?? "");
    setSummaryDraft(revision.summary ?? "");
    setTopicDraft(revision.topic ?? "");
    setSourceTitleDraft(revision.source_title ?? "");
    setSourceUrlDraft(revision.source_url ?? "");
    setBodyDraft(revision.body);
    setReason("");
    setScheduleAt("");
    setCommandState("idle");
    setCommandError(null);
  }

  async function createDraft() {
    if (effectiveRole !== "ops" && effectiveRole !== "superadmin") return;
    const typedKey = createKeyDraft.trim();
    const contentKey = typedKey;
    const normalizedReason = createReason.trim();
    if (!contentKey) {
      setCreateState("error");
      setCreateError("请填写内容键。");
      return;
    }
    if (prefix && !matchesContentScope(contentKey, prefix)) {
      setCreateState("error");
      setCreateError(`内容键必须属于 ${prefix} 命名空间。`);
      return;
    }
    if (
      contentPrefixes &&
      !contentPrefixes.some((candidate) => matchesContentScope(contentKey, candidate))
    ) {
      setCreateState("error");
      setCreateError("内容键必须属于当前 CMS 面板命名空间。");
      return;
    }
    if (!prefix && !contentPrefixes && !isRegisteredPageContentKey(contentKey)) {
      setCreateState("error");
      setCreateError("页面面板只允许已登记的 home、page、notice 或 seo 命名空间。");
      return;
    }
    if (!createBodyDraft.trim()) {
      setCreateState("error");
      setCreateError("正文不能为空。");
      return;
    }
    if (!normalizedReason) {
      setCreateState("error");
      setCreateError("请填写操作原因；原因会写入审计记录。");
      return;
    }

    const payload: Record<string, string> = {
      content_key: contentKey,
      locale: "zh-CN",
      body: createBodyDraft,
      reason: normalizedReason,
    };
    if (createTitleDraft.trim()) payload.title = createTitleDraft.trim();
    if (createSummaryDraft.trim()) payload.summary = createSummaryDraft.trim();
    if (createTopicDraft.trim()) payload.topic = createTopicDraft.trim();
    if (createSourceTitleDraft.trim()) payload.source_title = createSourceTitleDraft.trim();
    if (createSourceUrlDraft.trim()) payload.source_url = createSourceUrlDraft.trim();

    setCreateState("submitting");
    setCreateError(null);
    const created = await adminFetch<AdminContentRevision>("/api/v1/admin/cms", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!created.ok) {
      setCreateState("error");
      setCreateError(created.title);
      return;
    }

    const refreshed = await fetchContentIndex(prefix, contentPrefixes);
    if (!refreshed.ok) {
      setCreateState("error");
      setCreateError("CMS 草稿已创建，但列表刷新失败，请重新读取。");
      return;
    }
    setData(refreshed.data);
    setState(refreshed.data.revisions.length > 0 ? "ready" : "empty");
    setCreateKeyDraft("");
    setCreateTitleDraft("");
    setCreateSummaryDraft("");
    setCreateTopicDraft("");
    setCreateSourceTitleDraft("");
    setCreateSourceUrlDraft("");
    setCreateBodyDraft("");
    setCreateReason("");
    setCreateState("success");
    setCreateError(null);
  }

  async function runCommand(
    action: "edit" | "preview" | "schedule" | "publish" | "withdraw" | "archive" | "restore",
    revision: AdminContentHistoryResponse["revisions"][number],
  ) {
    const normalizedReason = reason.trim();
    if (!normalizedReason) {
      setCommandState("error");
      setCommandError("请填写操作原因；原因会写入审计记录。");
      return;
    }
    if (action === "edit" && !bodyDraft.trim()) {
      setCommandState("error");
      setCommandError("正文不能为空。");
      return;
    }
    if (action === "schedule" && !scheduleAt) {
      setCommandState("error");
      setCommandError("请选择未来的发布时间。");
      return;
    }

    const basePath = `/api/v1/admin/cms/${revision.revision_id}`;
    const editPayload: Record<string, string> = {
      body: bodyDraft,
      reason: normalizedReason,
    };
    if (titleDraft.trim()) editPayload.title = titleDraft.trim();
    if (summaryDraft.trim()) editPayload.summary = summaryDraft.trim();
    if (topicDraft.trim()) editPayload.topic = topicDraft.trim();
    if (sourceTitleDraft.trim()) editPayload.source_title = sourceTitleDraft.trim();
    if (sourceUrlDraft.trim()) editPayload.source_url = sourceUrlDraft.trim();
    const init: RequestInit = {
      method: action === "edit" ? "PATCH" : "POST",
      body: JSON.stringify(
        action === "edit"
          ? editPayload
          : action === "schedule"
            ? { publish_at: new Date(scheduleAt).toISOString(), reason: normalizedReason }
            : { reason: normalizedReason },
      ),
    };
    const endpoint =
      action === "edit"
        ? basePath
        : `${basePath}/${action}`;
    setCommandState("submitting");
    setCommandError(null);
    const response = await adminFetch<AdminContentIndexItem & { body: string }>(endpoint, init);
    if (!response.ok) {
      setCommandState("error");
      setCommandError(response.title);
      return;
    }

    const updated = response.data;
    setData((current) => ({
      revisions: current.revisions.map((item) =>
        item.content_key === updated.content_key && item.locale === updated.locale
          ? {
              revision_id: updated.revision_id,
              content_key: updated.content_key,
              locale: updated.locale,
              revision: updated.revision,
              state: updated.state,
              title: updated.title,
              summary: updated.summary,
              topic: updated.topic,
              source_title: updated.source_title,
              source_url: updated.source_url,
              author_ref: updated.author_ref,
              publish_at: updated.publish_at,
              withdrawn_reason: updated.withdrawn_reason,
              created_at: updated.created_at,
            }
          : item,
      ),
    }));
    const historyResponse = await adminFetch<AdminContentHistoryResponse>(
      `/api/v1/admin/cms/${encodeURIComponent(updated.content_key)}/history?locale=${encodeURIComponent(updated.locale)}`,
    );
    if (!historyResponse.ok) {
      setReason("");
      setScheduleAt("");
      setCommandState("error");
      setCommandError("CMS 命令已完成，但历史刷新失败，请重新读取。");
      return;
    }
    setHistory(historyResponse.data);
    const nextActive = historyResponse.data.revisions.find(
      (item) => item.revision_id === updated.revision_id,
    ) ?? historyResponse.data.revisions[0];
    setActiveRevisionId(nextActive?.revision_id ?? null);
    setTitleDraft(nextActive?.title ?? "");
    setSummaryDraft(nextActive?.summary ?? "");
    setTopicDraft(nextActive?.topic ?? "");
    setSourceTitleDraft(nextActive?.source_title ?? "");
    setSourceUrlDraft(nextActive?.source_url ?? "");
    setBodyDraft(nextActive?.body ?? "");
    setReason("");
    setScheduleAt("");
    setCommandState("success");
    setCommandError(null);
  }

  const rows: TableRow[] = data.revisions.map((item) => ({
    id: item.content_key,
    contentKey: item.content_key,
    title: item.title ?? "—",
    topic: item.topic ?? "—",
    revision: item.revision,
    state: STATE_COPY[item.state],
    author: item.author_ref,
    updatedAt: formatDate(item.created_at),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取 CMS 版本…" description="列表只读取版本元数据，不批量加载正文。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="CMS 内容只允许运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="CMS 平台暂不可用" description="页面不显示虚假的内容版本或发布态。" />
    ) : state === "error" ? (
      <Status state="error" title="CMS 版本读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无 CMS 版本" description="创建内容版本后，这里会显示真实的发布状态和责任人。" />
    ) : (
      <Status state="success" title="CMS 版本已接入" description="正文仍由具体内容历史接口按权限读取；此列表不回传正文。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state !== "forbidden" ? <section className={styles.panel} aria-labelledby="cms-list-title">
        <div className={styles.heading}>
          <div>
            <h2 id="cms-list-title">{title}</h2>
            <p>查看最新修订、发布态和责任人；内容正文不在批量索引中返回。</p>
          </div>
          <span className={styles.badge}>版本化</span>
        </div>
        <Table
          caption={`${title}版本列表`}
          columns={COLUMNS}
          rows={rows}
          filterLabel={`筛选${title}`}
          filterPlaceholder="例如：内容、状态或责任人…"
          pageSize={20}
          onRowActivate={(row) => void openHistory(String(row.contentKey))}
          rowActionLabel="查看历史"
          emptyState={state === "unavailable" ? "服务端内容事实暂不可用" : "当前没有内容版本"}
        />
      </section> : null}
      {effectiveRole === "ops" || effectiveRole === "superadmin" ? (
        <section className={styles.panel} aria-labelledby="cms-create-panel-title">
          <div className={styles.heading}>
            <div>
              <h2 id="cms-create-panel-title">创建内容草稿</h2>
              <p>
                只创建当前面板命名空间内的草稿；正文、元数据和操作原因会一起提交，创建成功后重新读取真实索引。
              </p>
            </div>
            <span className={styles.badge}>需要审计原因</span>
          </div>
          <div className={styles.commandField}>
            <label htmlFor="cms-create-key">内容键</label>
              <input
                id="cms-create-key"
                type="text"
                value={createKeyDraft}
                placeholder={prefix ? `${prefix}.example` : "例如 page.about"}
                onChange={(event) => setCreateKeyDraft(event.target.value)}
                disabled={createState === "submitting"}
              />
            <p className={styles.commandHelp}>
              {prefix
                ? `必须以 ${prefix} 或 ${prefix}. 开头。`
                : contentPrefixes
                  ? "必须属于当前 CMS 面板已登记的命名空间。"
                  : "允许 home.*、page.*、notice[.*] 和 seo.* 页面命名空间。"}
            </p>
          </div>
          <div className={styles.commandField}>
            <label htmlFor="cms-create-title">标题</label>
            <input
              id="cms-create-title"
              type="text"
              value={createTitleDraft}
              onChange={(event) => setCreateTitleDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-summary">摘要</label>
            <textarea
              id="cms-create-summary"
              rows={3}
              value={createSummaryDraft}
              onChange={(event) => setCreateSummaryDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-topic">主题</label>
            <input
              id="cms-create-topic"
              type="text"
              value={createTopicDraft}
              onChange={(event) => setCreateTopicDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-source-title">来源标题</label>
            <input
              id="cms-create-source-title"
              type="text"
              value={createSourceTitleDraft}
              onChange={(event) => setCreateSourceTitleDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-source-url">来源链接</label>
            <input
              id="cms-create-source-url"
              type="url"
              value={createSourceUrlDraft}
              onChange={(event) => setCreateSourceUrlDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-body">正文</label>
            <textarea
              id="cms-create-body"
              rows={7}
              value={createBodyDraft}
              onChange={(event) => setCreateBodyDraft(event.target.value)}
              disabled={createState === "submitting"}
            />
            <label htmlFor="cms-create-reason">新建操作原因</label>
            <textarea
              id="cms-create-reason"
              rows={3}
              value={createReason}
              onChange={(event) => setCreateReason(event.target.value)}
              aria-describedby={createError ? "cms-create-error" : "cms-create-reason-help"}
              aria-invalid={createState === "error" && !createReason.trim() ? "true" : undefined}
              disabled={createState === "submitting"}
              required
            />
            <p id="cms-create-reason-help" className={styles.commandHelp}>创建原因会写入 `cms.draft.created` 审计事件。</p>
          </div>
          {createError ? <p id="cms-create-error" className={styles.inlineAlert} role="alert">{createError}</p> : null}
          {createState === "success" ? (
            <Status state="success" title="CMS 草稿已创建" description="服务端已创建版本并完成列表刷新；发布仍需单独的审计命令。" />
          ) : null}
          <div className={styles.commandActions}>
            <button type="button" disabled={createState === "submitting"} onClick={() => void createDraft()}>
              创建草稿
            </button>
          </div>
        </section>
      ) : null}
      {selectedKey ? (
        <section className={styles.panel} aria-labelledby="cms-history-title">
          <div className={styles.heading}>
            <div>
              <h2 id="cms-history-title">修订历史</h2>
              <p>{selectedKey} 的正文版本来自服务端历史接口；下方命令要求原因并由服务端写入审计。</p>
            </div>
            <span className={styles.badge}>带审计命令</span>
          </div>
          {historyState === "loading" ? (
            <Status state="loading" title="正在读取修订历史…" description="只加载选中内容键的历史，不批量读取正文。" />
          ) : historyState === "error" ? (
            <Status state="error" title="修订历史读取失败" description={historyError ?? "请求失败，请重试。"} />
          ) : (
            <div className={styles.history}>
              {history.revisions.map((revision) => (
                <article className={styles.revision} key={revision.revision_id}>
                  <div className={styles.revisionHeading}>
                    <h3>修订 {revision.revision}</h3>
                    <span>{STATE_COPY[revision.state]}</span>
                  </div>
                  <p className={styles.revisionMeta}>
                    {revision.author_ref} · {formatDate(revision.created_at)}
                  </p>
                  {revision.title ? <p>标题：{revision.title}</p> : null}
                  {revision.summary ? <p>摘要：{revision.summary}</p> : null}
                  {revision.topic ? <p>主题：{revision.topic}</p> : null}
                  {revision.source_title ? (
                    <p>
                      来源：{revision.source_url ? (
                        <a href={revision.source_url}>{revision.source_title}</a>
                      ) : revision.source_title}
                    </p>
                  ) : null}
                  {activeRevisionId === revision.revision_id && revision.state === "draft" ? null : (
                    <pre className={styles.body}>{revision.body}</pre>
                  )}
                  <button
                    className={styles.selectRevision}
                    type="button"
                    aria-pressed={activeRevisionId === revision.revision_id}
                    onClick={() => selectRevision(revision)}
                  >
                    {activeRevisionId === revision.revision_id ? "当前操作对象" : `选择修订 ${revision.revision}`}
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
      {activeRevisionId && historyState === "ready" ? (() => {
        const revision = history.revisions.find((item) => item.revision_id === activeRevisionId);
        if (!revision) return null;
        const canEdit = revision.state === "draft";
        const canPreview = revision.state === "draft";
        const canSchedule = revision.state === "draft" || revision.state === "preview";
        const canPublish = revision.state === "draft" || revision.state === "preview";
        const canWithdraw = revision.state === "published";
        const canArchive = revision.state === "draft" || revision.state === "withdrawn";
        const canRestore = revision.state === "withdrawn";
        return (
          <section className={styles.panel} aria-labelledby="cms-command-title">
            <div className={styles.heading}>
              <div>
                <h2 id="cms-command-title">审计命令</h2>
                <p>当前对象：修订 {revision.revision} · {STATE_COPY[revision.state]}。每次变更都要求原因。</p>
              </div>
              <span className={styles.badge}>服务端 RBAC</span>
            </div>
            {revision.state === "draft" ? (
              <div className={styles.commandField}>
                <label htmlFor="cms-title-draft">标题 修订 {revision.revision}</label>
                <input
                  id="cms-title-draft"
                  type="text"
                  value={titleDraft}
                  onChange={(event) => setTitleDraft(event.target.value)}
                  disabled={commandState === "submitting"}
                />
                <label htmlFor="cms-summary-draft">摘要 修订 {revision.revision}</label>
                <textarea
                  id="cms-summary-draft"
                  value={summaryDraft}
                  onChange={(event) => setSummaryDraft(event.target.value)}
                  disabled={commandState === "submitting"}
                  rows={3}
                />
                <label htmlFor="cms-topic-draft">主题 修订 {revision.revision}</label>
                <input
                  id="cms-topic-draft"
                  type="text"
                  value={topicDraft}
                  onChange={(event) => setTopicDraft(event.target.value)}
                  disabled={commandState === "submitting"}
                />
                <label htmlFor="cms-source-title-draft">来源标题 修订 {revision.revision}</label>
                <input
                  id="cms-source-title-draft"
                  type="text"
                  value={sourceTitleDraft}
                  onChange={(event) => setSourceTitleDraft(event.target.value)}
                  disabled={commandState === "submitting"}
                />
                <label htmlFor="cms-source-url-draft">来源链接 修订 {revision.revision}</label>
                <input
                  id="cms-source-url-draft"
                  type="url"
                  value={sourceUrlDraft}
                  onChange={(event) => setSourceUrlDraft(event.target.value)}
                  disabled={commandState === "submitting"}
                />
                <label htmlFor="cms-body-draft">正文 修订 {revision.revision}</label>
                <textarea
                  id="cms-body-draft"
                  value={bodyDraft}
                  onChange={(event) => setBodyDraft(event.target.value)}
                  aria-describedby={commandError ? "cms-command-error" : "cms-body-help"}
                  aria-invalid={commandError && !bodyDraft.trim() ? "true" : undefined}
                  disabled={commandState === "submitting"}
                  rows={7}
                />
                <p id="cms-body-help" className={styles.commandHelp}>只允许编辑草稿；已发布正文不可原地修改。</p>
              </div>
            ) : null}
            {canSchedule ? (
              <div className={styles.commandField}>
                <label htmlFor="cms-schedule-at">计划发布时间</label>
                <input
                  id="cms-schedule-at"
                  type="datetime-local"
                  value={scheduleAt}
                  onChange={(event) => setScheduleAt(event.target.value)}
                  disabled={commandState === "submitting"}
                />
              </div>
            ) : null}
            <div className={styles.commandField}>
              <label htmlFor="cms-command-reason">操作原因</label>
              <textarea
                id="cms-command-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                aria-describedby={commandError ? "cms-command-error" : "cms-reason-help"}
                aria-invalid={commandState === "error" && !reason.trim() ? "true" : undefined}
                disabled={commandState === "submitting"}
                required
                rows={3}
              />
              <p id="cms-reason-help" className={styles.commandHelp}>原因会与操作者、内容键、版本和结果一起写入审计。</p>
            </div>
            {commandError ? <p id="cms-command-error" className={styles.inlineAlert} role="alert">{commandError}</p> : null}
            {commandState === "success" ? (
              <Status state="success" title="CMS 命令已完成" description="服务端已完成状态、权限、原因和审计校验，并重新读取历史。" />
            ) : null}
            <div className={styles.commandActions}>
              {canEdit ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("edit", revision)}>保存草稿</button> : null}
              {canPreview ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("preview", revision)}>送入预览</button> : null}
              {canSchedule ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("schedule", revision)}>安排发布</button> : null}
              {canPublish ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("publish", revision)}>发布</button> : null}
              {canWithdraw ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("withdraw", revision)}>撤回</button> : null}
              {canArchive ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("archive", revision)}>归档</button> : null}
              {canRestore ? <button type="button" disabled={commandState === "submitting"} onClick={() => void runCommand("restore", revision)}>恢复为新草稿</button> : null}
            </div>
          </section>
        );
      })() : null}
    </div>
  );
}
