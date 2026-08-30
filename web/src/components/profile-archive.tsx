"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  formatProfileOption,
  listProfiles,
  startPreviewReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import surface from "./app-surface.module.css";
import { ProfileRenameControl } from "./profile-rename-control";
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
  const router = useRouter();
  const searchParams = useSearchParams();
  const justCreated = searchParams.get("created") === "1";
  const [loading, setLoading] = useState(true);
  const [profiles, setProfiles] = useState<ProfileSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const intentKeyRef = useRef<IntentKey | null>(null);

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
    setActionError(null);
    setAttempt((value) => value + 1);
  }

  async function handleStartBazi(profileVersionId: string) {
    if (startingId) return;
    setStartingId(profileVersionId);
    setActionError(null);
    const payload = {
      profile_version_id: profileVersionId,
      query: "查看这个档案的事业与工作主题",
      dimension_ids: ["career"] as ("overview" | "career")[],
    };
    const intent = stableKeyForIntent(intentKeyRef.current, payload);
    intentKeyRef.current = intent;
    try {
      const response = await startPreviewReading(payload, intent.key);
      router.push(`/app/readings/${response.reading_version_id}`);
    } catch (err) {
      setActionError(errorMessage(err));
      setStartingId(null);
    }
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
          <Link className={surface.secondaryButton} href="/auth/login">
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
          actionHref="/account/profiles/new"
          actionLabel="开始建立档案"
        />
        <nav className={styles.emptyFlows} aria-label="可用入口">
          <span>没有档案时，仅一事一问可以直接开始：</span>
          <ul>
            <li>
              <Link href="/app/ask/liuyao">直接一事一问 · 六爻</Link>
            </li>
          </ul>
        </nav>
      </>
    );
  }

  const latest = profiles[0];

  return (
    <>
      {justCreated ? (
        <StatusPanel
          state="success"
          title="档案已保存"
          description="新的不可变档案版本已经落库。下一步可以直接看八字概览，或发起今日/近七日。"
          actionHref={`/app/bazi?profile=${encodeURIComponent(latest.profile_version_id)}`}
          actionLabel="查看八字概览"
        />
      ) : null}

      {actionError ? (
        <StatusPanel
          state="error"
          title="无法启动事业主题概览"
          description={actionError}
        />
      ) : null}

      <section className={surface.paper} aria-labelledby="profile-archive-title">
        <div className={surface.sectionHeader}>
          <div>
            <h2 id="profile-archive-title">已保存的档案版本</h2>
            <p>
              这里只展示服务端返回的安全字段。建档后先从这里看八字，或继续今日/近七日。
            </p>
          </div>
        </div>
        <ul className={styles.profileList}>
          {profiles.map((entry) => (
            <li key={entry.profile_version_id} className={styles.profileItem}>
              <div className={styles.profileMain}>
                <strong className={styles.profileName}>
                  {formatProfileOption(entry)}
                </strong>
                <span className={styles.profileMeta}>
                  确认于 {formatProfileTime(entry.created_at)}
                </span>
              </div>
              <div className={styles.profileActions}>
                <ProfileRenameControl
                  profile={entry}
                  onRenamed={(next) => {
                    setProfiles((current) =>
                      current?.map((item) =>
                        item.profile_id === next.profile_id ? { ...item, ...next } : item,
                      ) ?? null,
                    );
                  }}
                />
                <button
                  type="button"
                  className={surface.secondaryButton}
                  disabled={startingId === entry.profile_version_id}
                  aria-busy={startingId === entry.profile_version_id}
                  onClick={() => handleStartBazi(entry.profile_version_id)}
                >
                  {startingId === entry.profile_version_id
                    ? "正在启动事业主题…"
                    : "查看事业主题概览"}
                </button>
                <Link
                  className={surface.secondaryButton}
                  href={`/app/fortune/today?profile=${encodeURIComponent(entry.profile_version_id)}`}
                >
                  今日
                </Link>
                <Link
                  className={surface.secondaryButton}
                  href={`/app/fortune/week?profile=${encodeURIComponent(entry.profile_version_id)}`}
                >
                  近七日
                </Link>
              </div>
            </li>
          ))}
        </ul>
        <div className={surface.actionRow}>
          <Link className={surface.secondaryButton} href="/account/profiles/new">
            新建档案版本
          </Link>
          <Link className={surface.secondaryButton} href="/app/bazi">
            选择档案并查看事业主题
          </Link>
          <Link className={surface.secondaryButton} href="/account/history">
            查看解读历史
          </Link>
        </div>
      </section>
    </>
  );
}
