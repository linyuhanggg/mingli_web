"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AppPageHeader } from "@/components/app-page-header";
import {
  ApiError,
  listProfileVersions,
  type ProfileSummary,
} from "@/lib/api";

import { StatusPanel } from "../status-panel";
import { SecondaryStatus } from "./secondary-status";
import styles from "./secondary-surfaces.module.css";
import profileStyles from "../profile-archive.module.css";
import surface from "../app-surface.module.css";

type AccountProfileDetailSurfaceProps = {
  readonly profileId: string;
};

function formatVersionTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "读取档案版本失败，请稍后重试。";
}

function ProfileVersionHistory({ profileId }: AccountProfileDetailSurfaceProps) {
  const [loading, setLoading] = useState(true);
  const [versions, setVersions] = useState<ProfileSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    listProfileVersions(profileId)
      .then(({ versions: next }) => {
        if (!cancelled) setVersions(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setSessionExpired(true);
        } else {
          setError(errorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [attempt, profileId]);

  function retry() {
    setLoading(true);
    setVersions(null);
    setError(null);
    setSessionExpired(false);
    setAttempt((value) => value + 1);
  }

  if (loading) {
    return (
      <StatusPanel
        state="loading"
        title="正在读取档案版本"
        description="服务端正在返回这份 SubjectProfile 的不可变版本摘要。"
      />
    );
  }

  if (error) {
    return (
      <>
        <StatusPanel state="error" title="无法读取档案版本" description={error} />
        <button className={surface.secondaryButton} type="button" onClick={retry}>
          重试
        </button>
      </>
    );
  }

  if (sessionExpired) {
    return (
      <StatusPanel
        state="error"
        title="登录已过期"
        description="登录状态已失效，档案版本暂时无法读取；重新登录后可回到这里。"
        actionHref="/auth/login"
        actionLabel="重新登录"
      />
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <StatusPanel
        state="empty"
        title="还没有可显示的版本"
        description="服务端没有返回属于当前账户的档案版本；不会根据网址补出资料。"
        actionHref="/account/profiles"
        actionLabel="返回档案列表"
      />
    );
  }

  return (
    <section className={surface.paper} aria-labelledby="profile-version-history-title">
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="profile-version-history-title">档案版本历史</h2>
          <p>这里只展示服务端返回的版本号和确认时间，不展示出生资料正文。</p>
        </div>
      </div>
      <ul className={profileStyles.profileList}>
        {versions.map((version) => (
          <li className={profileStyles.profileItem} key={version.profile_version_id}>
            <div className={profileStyles.profileMain}>
              <strong className={profileStyles.profileName}>档案 v{version.version}</strong>
              <span className={profileStyles.profileMeta}>
                确认于 {formatVersionTime(version.created_at)}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <Link className={surface.secondaryButton} href="/account/profiles">
        返回档案列表
      </Link>
    </section>
  );
}

function AccountProfileDetailContent({ profileId }: AccountProfileDetailSurfaceProps) {
  const { state } = useAccountSession();

  if (state.status === "checking") {
    return (
      <StatusPanel
        state="loading"
        title="正在确认档案访问权限"
        description="先确认当前账户会话，再读取属于你的 ProfileVersion 历史。"
      />
    );
  }

  if (state.status === "error") {
    return (
      <StatusPanel
        state="error"
        title="暂时无法确认档案访问权限"
        description={state.message}
      />
    );
  }

  if (state.status === "signedOut") {
    return (
      <SecondaryStatus
        action={{ href: "/auth/login", label: "前往登录" }}
        description="登录后才能查看属于当前账户的档案版本；不会根据网址猜测资料。"
        state="need-login"
        title="需要登录"
      />
    );
  }

  return <ProfileVersionHistory profileId={profileId} />;
}

export function AccountProfileDetailSurface({ profileId }: AccountProfileDetailSurfaceProps) {
  return (
    <AccountSessionBoundary>
      <div className={styles.accountPage}>
        <AppPageHeader
          description="网址中的标识只用于请求服务端所有权校验，不会被用来推断或公开出生资料。"
          title="档案版本与授权边界"
        />
        <section aria-label="个人中心 · 档案详情" className={styles.accountPanel}>
          <AccountProfileDetailContent profileId={profileId} />
        </section>
      </div>
    </AccountSessionBoundary>
  );
}
