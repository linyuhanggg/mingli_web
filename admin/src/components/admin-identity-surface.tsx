"use client";

import { useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminIdentityKind,
  AdminSubjectResponse,
  AdminSubjectsResponse,
  AdminUserResponse,
  AdminUsersResponse,
} from "@/lib/admin-identity";

import styles from "./admin-identity-surface.module.css";

const LIST_COLUMNS: Record<"users" | "subjects", TableColumn[]> = {
  users: [
    { key: "id", header: "身份", sortable: true },
    { key: "sessions", header: "会话" },
    { key: "consents", header: "同意" },
    { key: "facts", header: "资料" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  subjects: [
    { key: "id", header: "Subject", sortable: true },
    { key: "owner", header: "所有者" },
    { key: "label", header: "标签" },
    { key: "versions", header: "资料版本" },
    { key: "status", header: "状态", sortable: true },
  ],
};

type SurfaceState = "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusCopy(value: string): string {
  return {
    active: "正常",
    closed: "已关闭",
    revoked: "已撤销",
    expired: "已过期",
    deleted: "已删除",
  }[value] ?? value;
}

function genderCopy(value: "male" | "female" | "other"): string {
  return { male: "男", female: "女", other: "其他" }[value];
}

function profilePolicyCopy(value: "civil" | "solar" | "lunar"): string {
  return { civil: "民用时间", solar: "真太阳时", lunar: "农历口径" }[value];
}

function ziHourPolicyCopy(value: "midnight" | "substitute" | "solar"): string {
  return { midnight: "午夜换日", substitute: "子初换日", solar: "太阳时换日" }[value];
}

function endpoint(kind: AdminIdentityKind, id?: string): string {
  if (kind === "users") return "/api/v1/admin/users";
  if (kind === "subjects") return "/api/v1/admin/subjects";
  if (!id) throw new Error(`Missing identity detail id for ${kind}`);
  return kind === "user-detail"
    ? `/api/v1/admin/users/${id}`
    : `/api/v1/admin/subjects/${id}`;
}

function isDetail(kind: AdminIdentityKind): kind is "user-detail" | "subject-detail" {
  return kind === "user-detail" || kind === "subject-detail";
}

function listCount(kind: "users" | "subjects", data: AdminUsersResponse | AdminSubjectsResponse): number {
  return kind === "users" && "users" in data ? data.users.length : "subjects" in data ? data.subjects.length : 0;
}

function userRows(data: AdminUsersResponse): TableRow[] {
  return data.users.map((item) => ({
    id: item.id,
    consents: `${item.consent_count} 条同意`,
    status: statusCopy(item.status),
    facts: `${item.identity_count} 个身份 · ${item.consent_count} 条同意 · ${item.subject_count} 个 Subject`,
    sessions: `${item.active_session_count} 个活跃会话`,
    updatedAt: formatDate(item.created_at),
  }));
}

function subjectRows(data: AdminSubjectsResponse): TableRow[] {
  return data.subjects.map((item) => ({
    id: item.id,
    owner: item.owner_user_id ?? "游客 Subject",
    label: item.label ?? "未命名",
    versions: `${item.version_count} 个版本${item.latest_version ? ` · 最新 v${item.latest_version}` : ""}`,
    status: statusCopy(item.status),
  }));
}

function DetailDefinitions({
  items,
}: {
  items: readonly { label: string; value: string }[];
}) {
  return (
    <dl className={styles.definitions}>
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DetailPlaceholder({
  kind,
  id,
}: {
  kind: "user-detail" | "subject-detail";
  id?: string;
}) {
  const isUser = kind === "user-detail";
  return (
    <section
      className={styles.panel}
      aria-labelledby={isUser ? "user-detail-facts-title" : "subject-detail-title"}
    >
      <div className={styles.heading}>
        <div>
          <h2 id={isUser ? "user-detail-facts-title" : "subject-detail-title"}>
            {isUser ? "用户详情字段" : "Subject 详情字段"}
          </h2>
          <p>
            {isUser
              ? "保留用户、身份、同意、设备会话和 Subject 的详情结构；服务端事实恢复后才显示具体值。"
              : "保留 Subject、版本、授权和业务资料详情结构；服务端事实恢复后才显示具体值。"}
          </p>
        </div>
        <span className={styles.badge}>只读事实</span>
      </div>
      <DetailDefinitions
        items={[
          { label: isUser ? "用户" : "Subject", value: id ?? "待平台解析" },
          { label: "数据状态", value: "服务端事实暂不可用" },
        ]}
      />
    </section>
  );
}

function UserDetail({ data }: { data: AdminUserResponse }) {
  return (
    <>
      <section className={styles.panel} aria-labelledby="user-detail-facts-title">
        <div className={styles.heading}>
          <div>
            <h2 id="user-detail-facts-title">用户详情字段</h2>
            <p>显示授权可见的身份目标、同意、设备会话和 Subject 元数据；不读取密码或密文材料。</p>
          </div>
          <span className={styles.badge}>只读事实</span>
        </div>
        <DetailDefinitions
          items={[
            { label: "用户", value: data.id },
            { label: "状态", value: statusCopy(data.status) },
            { label: "创建时间", value: formatDate(data.created_at) },
            { label: "身份数量", value: String(data.identities.length) },
            { label: "同意数量", value: String(data.consents.length) },
            { label: "Subject 数量", value: String(data.subjects.length) },
          ]}
        />
      </section>
      <section className={styles.panel} aria-labelledby="user-identities-title">
        <div className={styles.heading}>
          <div>
            <h2 id="user-identities-title">身份、同意与设备</h2>
            <p>授权员工可查看服务端解密后的身份目标；设备只展示状态和时间，不展示 token 材料。</p>
          </div>
        </div>
        <Table
          caption="登录身份"
          columns={[
            { key: "id", header: "身份", sortable: true },
            { key: "provider", header: "提供方" },
            { key: "destination", header: "身份目标" },
            { key: "status", header: "状态" },
          ]}
          rows={data.identities.map((item) => ({
            id: item.id,
            provider: item.provider,
            destination: item.destination ?? item.masked_destination,
            status: statusCopy(item.status),
          }))}
          emptyState="暂无登录身份"
        />
        <Table
          caption="设备会话"
          columns={[
            { key: "id", header: "会话", sortable: true },
            { key: "status", header: "状态" },
            { key: "lastSeen", header: "最近活动" },
            { key: "expires", header: "到期" },
          ]}
          rows={data.sessions.map((item) => ({
            id: item.id,
            status: statusCopy(item.status),
            lastSeen: formatDate(item.last_seen_at),
            expires: formatDate(item.expires_at),
          }))}
          emptyState="暂无设备会话"
        />
      </section>
      <section className={styles.panel} aria-labelledby="user-consents-title">
        <div className={styles.heading}>
          <div>
            <h2 id="user-consents-title">政策同意与 Subject</h2>
            <p>政策只显示版本事实，Subject 只显示版本数量和最新版本号。</p>
          </div>
        </div>
        <Table
          caption="政策同意"
          columns={[
            { key: "id", header: "同意记录", sortable: true },
            { key: "policy", header: "政策" },
            { key: "context", header: "场景" },
            { key: "accepted", header: "同意时间" },
          ]}
          rows={data.consents.map((item) => ({
            id: item.id,
            policy: `${item.policy_key} · ${item.policy_version}`,
            context: item.context,
            accepted: formatDate(item.accepted_at),
          }))}
          emptyState="暂无政策同意记录"
        />
        <Table
          caption="用户 Subject"
          columns={[
            { key: "id", header: "Subject", sortable: true },
            { key: "label", header: "标签" },
            { key: "versions", header: "版本" },
            { key: "status", header: "状态" },
          ]}
          rows={data.subjects.map((item) => ({
            id: item.id,
            label: item.label ?? "未命名",
            versions: `${item.version_count} 个版本${item.latest_version ? ` · 最新 v${item.latest_version}` : ""}`,
            status: statusCopy(item.status),
          }))}
          emptyState="暂无 Subject"
        />
      </section>
    </>
  );
}

function SubjectDetail({ data }: { data: AdminSubjectResponse }) {
  return (
    <section className={styles.panel} aria-labelledby="subject-detail-title">
        <div className={styles.heading}>
          <div>
            <h2 id="subject-detail-title">Subject 资料版本</h2>
            <p>授权员工可直接查看解密后的业务资料事实；密文、密钥材料和照片正文不进入 Admin 响应。</p>
        </div>
        <span className={styles.badge}>版本只读</span>
      </div>
      <DetailDefinitions
        items={[
          { label: "Subject", value: data.id },
          { label: "所有者", value: data.owner_user_id ?? "游客会话" },
          { label: "标签", value: data.label ?? "未命名" },
          { label: "状态", value: statusCopy(data.status) },
          { label: "创建时间", value: formatDate(data.created_at) },
        ]}
      />
      <div className={styles.versions} aria-label="资料版本列表">
        {data.versions.length === 0 ? <p>暂无资料版本</p> : null}
        {data.versions.map((item) => {
          const authorization = item.authorization;
          const profile = item.profile;
          return (
            <article className={styles.version} key={item.id}>
              <h3>版本 v{item.version}</h3>
              <p>创建于 {formatDate(item.created_at)}</p>
              <DetailDefinitions
                items={[
                  { label: "出生时间", value: profile.birth_datetime },
                  { label: "时区", value: profile.timezone },
                  { label: "地点", value: profile.location },
                  { label: "性别", value: genderCopy(profile.gender) },
                  { label: "时间口径", value: profilePolicyCopy(profile.time_basis_policy) },
                  { label: "子时口径", value: ziHourPolicyCopy(profile.zi_hour_policy) },
                  {
                    label: "经纬度",
                    value:
                      profile.longitude === null || profile.latitude === null
                        ? "未提供"
                        : `${profile.longitude}, ${profile.latitude}`,
                  },
                  { label: "坐标来源", value: profile.coordinate_source ?? "未提供" },
                ]}
              />
              <p>{authorization?.subject_type === "self" ? "本人授权" : "他人授权"}</p>
              <p>{authorization?.photo_authorization_confirmed ? "照片授权已确认" : "照片授权未确认"}</p>
              <p>{authorization?.difference_acknowledged ? "已确认差异说明" : "未确认差异说明"}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function AdminIdentitySurface({
  kind,
  id,
  role,
}: {
  kind: AdminIdentityKind;
  id?: string;
  role?: StaffRole;
}) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<SurfaceState>("loading");
  const [data, setData] = useState<AdminUsersResponse | AdminSubjectsResponse | AdminUserResponse | AdminSubjectResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminUsersResponse | AdminSubjectsResponse | AdminUserResponse | AdminSubjectResponse>(endpoint(kind, id));
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
      const count = !isDetail(kind) ? listCount(kind, response.data as AdminUsersResponse | AdminSubjectsResponse) : 1;
      setState(count > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, [id, kind]);

  const rows = useMemo(() => {
    if (kind === "users" && data && "users" in data) return userRows(data);
    if (kind === "subjects" && data && "subjects" in data) {
      return subjectRows(data as AdminSubjectsResponse);
    }
    return [];
  }, [data, kind]);

  const title = kind.startsWith("user") ? "用户与身份" : "Subject 与资料版本";
  const description = kind.startsWith("user")
    ? "读取授权可见的用户身份、设备、同意和 Subject 元数据，不展示密码或密文材料。"
    : "读取 Subject 版本、授权事实和解密后的业务资料，不展示密文、密钥材料或照片正文。";
  const notice =
    state === "loading" ? (
      <Status state="loading" title={`正在读取${title}…`} description={description} />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="用户与 Subject 资料只允许授权员工查看。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="身份平台暂不可用" description="页面不显示虚假的用户、设备或资料状态。" />
    ) : state === "error" ? (
      <Status state="error" title={`${title}读取失败`} description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title={`暂无${title}记录`} description={description} />
    ) : (
      <Status state="success" title={`${title}已接入`} description={description} />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {isDetail(kind) ? (
        state === "ready" && data ? (
          kind === "user-detail" && "identities" in data ? (
            <UserDetail data={data} />
          ) : "versions" in data ? (
            <SubjectDetail data={data} />
          ) : (
            <DetailPlaceholder kind={kind} id={id} />
          )
        ) : (
          <DetailPlaceholder kind={kind} id={id} />
        )
      ) : state !== "forbidden" ? (
        <section className={styles.panel} aria-labelledby={`${kind}-title`}>
          <div className={styles.heading}>
            <div>
              <h2 id={`${kind}-title`}>{title}</h2>
              <p>{description}</p>
            </div>
            <span className={styles.badge}>只读事实</span>
          </div>
          <Table
            caption={title}
            columns={LIST_COLUMNS[kind as "users" | "subjects"]}
            rows={rows}
            filterLabel={`筛选${title}`}
            filterPlaceholder="例如：编号、状态或标签…"
            pageSize={20}
            emptyState={state === "unavailable" ? "服务端事实暂不可用" : `当前没有${title}记录`}
          />
        </section>
      ) : null}
    </div>
  );
}
