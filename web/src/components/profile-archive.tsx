"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import * as profileApi from "@/lib/api";

import {
  ApiError,
  formatProfileOption,
  listProfiles,
  startPreviewReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";
import {
  consumeProfileSavedFlash,
  profileBirthDate,
  profileDisplayName,
} from "@/lib/profile-display-metadata";

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

type ProfileDisplayFields = {
  readonly display_name?: string | null;
  readonly birth_date?: string | null;
};

type DisplayProfile = ProfileSummary & ProfileDisplayFields;

async function persistProfileDisplayName(
  profileId: string,
  displayName: string,
): Promise<DisplayProfile> {
  const injectedUpdate = (profileApi as typeof profileApi & {
    updateProfileDisplayName?: (
      targetProfileId: string,
      targetDisplayName: string,
    ) => Promise<DisplayProfile>;
  }).updateProfileDisplayName;
  if (injectedUpdate) {
    return injectedUpdate(profileId, displayName);
  }

  const csrf = await profileApi.getCsrfToken();
  const response = await fetch(`/api/v1/profiles/${encodeURIComponent(profileId)}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify({ display_name: displayName }),
  });
  const body = response.headers.get("content-type")?.includes("json")
    ? await response.json() as DisplayProfile & { title?: string }
    : null;
  if (!response.ok || !body) {
    throw new ApiError(body?.title ?? "名称保存失败，请稍后重试。", response.status);
  }
  return body;
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
  const [savedFlash, setSavedFlash] = useState(() =>
    justCreated ? consumeProfileSavedFlash() : null,
  );
  const [showSavedBanner, setShowSavedBanner] = useState(justCreated);
  const [renamingProfileId, setRenamingProfileId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
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

  function startRename(profile: ProfileSummary) {
    setRenamingProfileId(profile.profile_id);
    setRenameValue(profileDisplayName(profile));
    setRenameError("");
  }

  async function saveRename(profile: ProfileSummary) {
    const nextName = renameValue.trim();
    if (!nextName) {
      setRenameError("请填写档案名称");
      return;
    }
    setRenameBusy(true);
    setRenameError("");
    try {
      const updated = await persistProfileDisplayName(profile.profile_id, nextName);
      setProfiles((current) =>
        current?.map((entry) =>
          entry.profile_id === updated.profile_id ? updated : entry,
        ) ?? current,
      );
      if (savedFlash?.profileId === profile.profile_id) {
        const returnedName = updated.display_name?.trim();
        if (updated.profile_id === profile.profile_id && returnedName) {
          setSavedFlash({
            name: profileDisplayName(updated),
            profileId: updated.profile_id,
          });
        } else {
          setShowSavedBanner(false);
        }
      }
      setRenamingProfileId(null);
      setRenameValue("");
    } catch (reason) {
      setRenameError(
        reason instanceof Error ? reason.message : "名称保存失败，请稍后重试。",
      );
    } finally {
      setRenameBusy(false);
    }
  }

  if (loading) {
    return (
      <StatusPanel
        state="loading"
        title="正在读取档案…"
        description="正在准备档案列表，请稍候。"
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
  const hasDisplayMetadata = profiles.some(
    (profile) => "display_name" in profile || "birth_date" in profile,
  );

  return (
    <>
      {showSavedBanner ? (
        <StatusPanel
          state="success"
          title={savedFlash ? `“${savedFlash.name}”已保存` : "档案已保存"}
          description="下一步可以直接查看八字概览，或发起今日、近七日主题。"
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
            <h2 id="profile-archive-title">
              {hasDisplayMetadata ? "已保存的档案" : "已保存的档案版本"}
            </h2>
            <p>
              {hasDisplayMetadata
                ? "名称用于帮助辨认；每次更新都会保留一个可回看的版本。"
                : "这里只展示服务端返回的安全字段。建档后先从这里看八字，或继续今日/近七日。"}
            </p>
          </div>
        </div>
        <ul className={styles.profileList}>
          {profiles.map((entry) => (
            <li key={entry.profile_version_id} className={styles.profileItem}>
              <div className={styles.profileMain}>
                {renamingProfileId === entry.profile_id ? (
                  <div aria-busy={renameBusy} className={styles.renameRow}>
                    <label className={styles.srOnly} htmlFor={`rename-${entry.profile_id}`}>
                      档案名称
                    </label>
                    <input
                      aria-describedby={renameError ? `rename-error-${entry.profile_id}` : undefined}
                      aria-invalid={Boolean(renameError)}
                      autoFocus
                      disabled={renameBusy}
                      id={`rename-${entry.profile_id}`}
                      maxLength={80}
                      onChange={(event) => {
                        setRenameValue(event.currentTarget.value);
                        if (renameError) setRenameError("");
                      }}
                      value={renameValue}
                    />
                    <button
                      aria-busy={renameBusy}
                      disabled={renameBusy}
                      type="button"
                      onClick={() => void saveRename(entry)}
                    >
                      {renameBusy ? "正在保存…" : "保存名称"}
                    </button>
                    <button
                      data-variant="secondary"
                      disabled={renameBusy}
                      type="button"
                      onClick={() => setRenamingProfileId(null)}
                    >
                      取消
                    </button>
                    {renameError ? (
                      <span id={`rename-error-${entry.profile_id}`} role="alert">
                        {renameError}
                      </span>
                    ) : null}
                  </div>
                ) : (
                  <strong className={styles.profileName}>
                    {hasDisplayMetadata
                      ? profileDisplayName(entry)
                      : formatProfileOption(entry)}
                  </strong>
                )}
                <span className={styles.profileMeta}>
                  {profileBirthDate(entry)} · v{entry.version} · 更新于 {formatProfileTime(entry.created_at)}
                </span>
              </div>
              <div className={styles.profileActions}>
                <button
                  type="button"
                  className={surface.secondaryButton}
                  onClick={() => startRename(entry)}
                >
                  重命名
                </button>
                <Link
                  className={surface.secondaryButton}
                  href={`/account/profiles/${encodeURIComponent(entry.profile_id)}`}
                >
                  查看版本
                </Link>
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
