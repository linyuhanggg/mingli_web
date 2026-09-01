"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AccountSessionBoundary, useAccountSession } from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import {
  ApiError,
  listProfileVersions,
  type ProfileSummary,
} from "@/lib/api";

import { StatusPanel } from "../status-panel";
import { LocalLoader } from "../ui";
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
      <section
        aria-busy="true"
        aria-labelledby="profile-version-history-loading-title"
        className={`${surface.paper} ${profileStyles.archivePanel}`}
      >
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="profile-version-history-loading-title">档案版本历史</h2>
            <p>正在读取这份档案的不可变版本记录。</p>
          </div>
        </div>
        <div className={profileStyles.loadingRow}>
          <LocalLoader label="正在读取档案版本…" />
          <p className={profileStyles.loadingText}>正在读取档案版本…</p>
        </div>
      </section>
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
        description="登录已失效，请重新登录后再查看。"
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
        description="这份档案还没有可显示的版本。"
        actionHref="/account/profiles"
        actionLabel="返回档案列表"
      />
    );
  }

  return (
    <section
      className={`${surface.paper} ${profileStyles.archivePanel}`}
      aria-labelledby="profile-version-history-title"
    >
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="profile-version-history-title">档案版本历史</h2>
          <p>只展示版本号和确认时间。</p>
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
        description="正在确认账户。"
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
        description="登录后才能查看档案。"
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
      <AccountSectionShell intro="查看这份档案的版本。" title="档案">
        <section aria-label="档案详情" className={styles.accountPanel}>
          <AccountProfileDetailContent profileId={profileId} />
        </section>
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
