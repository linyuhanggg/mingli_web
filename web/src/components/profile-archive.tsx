"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, listProfiles, type ProfileSummary } from "@/lib/api";

import surface from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";

import styles from "./profile-archive.module.css";


const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatProfileTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateTimeFormatter.format(date);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "读取档案失败，请稍后重试。";
}

export function ProfileArchive() {
  const [loading, setLoading] = useState(true);
  const [profiles, setProfiles] = useState<ProfileSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    listProfiles()
      .then(({ profiles: next }) => {
        if (cancelled) {
          return;
        }
        setProfiles(next);
      })
      .catch((err: unknown) => {
        if (!cancelled && err instanceof ApiError && err.status === 401) {
          setSessionExpired(true);
        } else if (!cancelled) {
          setError(errorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  function handleRetry() {
    setLoading(true);
    setError(null);
    setSessionExpired(false);
    setProfiles(null);
    setAttempt((value) => value + 1);
  }

  if (loading) {
    return (
      <StatusPanel
        state="loading"
        title="正在读取档案…"
        description="不可变档案版本正在抵达，请稍候。"
      />
    );
  }

  if (error) {
    return (
      <>
        <StatusPanel state="error" title="无法读取档案" description={error} />
        <div className={styles.retryRow}>
          <button className={surface.secondaryButton} type="button" onClick={handleRetry}>
            重试
          </button>
        </div>
      </>
    );
  }

  if (sessionExpired) {
    return (
      <>
        <StatusPanel
          state="error"
          title="登录已过期"
          description="登录状态已失效，档案暂时无法读取；重新登录后可回到这里。"
        />
        <div className={styles.retryRow}>
          <Link className={surface.secondaryButton} href="/account">
            重新登录
          </Link>
        </div>
      </>
    );
  }

  if (profiles === null || profiles.length === 0) {
    return (
      <>
        <StatusPanel
          state="empty"
          title="还没有已保存的档案"
          description="先核对出生资料并确认一次；服务端成功落库后，这里才会出现不可变档案版本。"
          actionHref="/app/profile/new"
          actionLabel="开始建立档案"
        />
        <section className={surface.paper} aria-labelledby="profile-flows-title">
          <div className={surface.sectionHeader}>
            <div>
              <h2 id="profile-flows-title">从这里进入可用流程</h2>
              <p>今日与近七日解读都从已保存的档案版本出发。</p>
            </div>
          </div>
          <ul className={styles.flowList}>
            <li>
              <Link href="/app/fortune/today">发起今日解读</Link>
            </li>
            <li>
              <Link href="/app/fortune/week">发起近七日解读</Link>
            </li>
            <li>
              <Link href="/app/profile/new">修改并保存新版本</Link>
            </li>
          </ul>
        </section>
      </>
    );
  }

  return (
    <section className={surface.paper} aria-labelledby="profile-archive-title">
      <div className={surface.sectionHeader}>
        <div>
          <h2 id="profile-archive-title">已保存的档案版本</h2>
          <p>这里只展示服务端返回的安全字段，不包含加密载荷或设备内草稿。</p>
        </div>
      </div>
      <ul className={styles.profileList}>
        {profiles.map((entry) => (
          <li key={entry.profile_version_id} className={styles.profileItem}>
            <strong className={styles.profileName}>档案 v{entry.version}</strong>
            <span className={styles.profileMeta}>
              {formatProfileTime(entry.created_at)}
            </span>
          </li>
        ))}
      </ul>
      <div className={surface.actionRow}>
        <Link className={surface.secondaryButton} href="/app/profile/new">
          新建档案版本
        </Link>
        <Link className={surface.secondaryButton} href="/app/fortune/today">
          发起今日解读
        </Link>
        <Link className={surface.secondaryButton} href="/app/fortune/week">
          发起近七日解读
        </Link>
      </div>
    </section>
  );
}
