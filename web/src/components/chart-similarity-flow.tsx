"use client";

import clsx from "clsx";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ButtonLink } from "@/components/button-link";
import {
  formatProfileOption,
  listProfiles,
  startChartSimilarityReading,
  type ChartSimilarityStartRequest,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

export function ChartSimilarityFlow() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedLeft = searchParams.get("left") ?? "";
  const requestedRight = searchParams.get("right") ?? "";
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [leftProfileId, setLeftProfileId] = useState("");
  const [rightProfileId, setRightProfileId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const busyRef = useRef(false);
  const intentKeyRef = useRef<IntentKey | null>(null);

  useEffect(() => {
    let active = true;
    listProfiles()
      .then((data) => {
        if (!active) return;
        const nextProfiles = data.profiles;
        setProfiles(nextProfiles);
        const available = new Set(
          nextProfiles.map((profile) => profile.profile_version_id),
        );
        const nextLeft = available.has(requestedLeft)
          ? requestedLeft
          : nextProfiles[0]?.profile_version_id ?? "";
        const nextRight =
          available.has(requestedRight) && requestedRight !== nextLeft
            ? requestedRight
            : nextProfiles.find(
                (profile) => profile.profile_version_id !== nextLeft,
              )?.profile_version_id ?? "";
        setLeftProfileId(nextLeft);
        setRightProfileId(nextRight);
        setLoading(false);
      })
      .catch((reason) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "档案加载失败，请稍后重试。");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadAttempt, requestedLeft, requestedRight]);

  const handleStart = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (busyRef.current) return;
      if (!leftProfileId || !rightProfileId) {
        setSubmitError("请选择两份已确认的档案版本。");
        return;
      }
      if (leftProfileId === rightProfileId) {
        setSubmitError("左右两侧必须选择不同的档案版本。");
        return;
      }

      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const payload: ChartSimilarityStartRequest = {
        profile_version_ids: [leftProfileId, rightProfileId],
        query: "请比较两份已确认命盘的八字四柱事实。",
        dimension_ids: ["state"],
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await startChartSimilarityReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "同盘事实任务启动失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [leftProfileId, rightProfileId, router],
  );

  function retryLoad() {
    setLoading(true);
    setError("");
    setLoadAttempt((attempt) => attempt + 1);
  }

  return (
    <div className={styles.wrap}>
      <h1>比较两份命盘的八字四柱事实</h1>
      <p className={styles.lead}>
        选择两份已经确认的档案版本，由服务端 Runtime 逐柱比较年、月、日、时四柱原值。
      </p>
      <p className={styles.scopeNotice}>
        <strong>当前只比较四柱原值，不生成相似度分数。</strong>
        结果不代表合婚、缘分、性格相似度或现实决定；浏览器不会重新排盘。
      </p>

      {loading ? <p className={styles.status} role="status">正在加载档案…</p> : null}

      {!loading && error ? (
        <div className={styles.state} role="alert">
          <p className={styles.error}>{error}</p>
          <button
            className={clsx(formControls.action, formControls.actionSecondary)}
            type="button"
            onClick={retryLoad}
          >
            重新加载
          </button>
        </div>
      ) : null}

      {!loading && !error && profiles.length === 0 ? (
        <div className={styles.state}>
          <p>还没有可用的档案。请先建立并确认档案版本。</p>
          <ButtonLink href="/app/profile/new">去建档</ButtonLink>
        </div>
      ) : null}

      {!loading && !error && profiles.length === 1 ? (
        <div className={styles.state}>
          <p>当前只有一份已确认档案；同盘比较需要两份不同的档案版本。</p>
          <ButtonLink href="/app/profiles">管理档案版本</ButtonLink>
        </div>
      ) : null}

      {!loading && !error && profiles.length > 1 ? (
        <form
          className={styles.form}
          onSubmit={handleStart}
          noValidate
          aria-busy={busy}
          aria-label="同盘匹配输入"
        >
          <div className={formControls.field}>
            <label htmlFor="chart-similarity-left">左侧已确认档案</label>
            <select
              id="chart-similarity-left"
              className={formControls.input}
              value={leftProfileId}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(submitError && !leftProfileId)}
              onChange={(event) => setLeftProfileId(event.target.value)}
            >
              <option value="">请选择左侧档案</option>
              {profiles.map((profile) => (
                <option key={profile.profile_version_id} value={profile.profile_version_id}>
                  {formatProfileOption(profile)}
                </option>
              ))}
            </select>
            <p className={formControls.hint}>
              只读取服务端已确认的 ProfileVersion，不在 URL 中放出生资料。
            </p>
          </div>

          <div className={formControls.field}>
            <label htmlFor="chart-similarity-right">右侧已确认档案</label>
            <select
              id="chart-similarity-right"
              className={formControls.input}
              value={rightProfileId}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(submitError && !rightProfileId)}
              onChange={(event) => setRightProfileId(event.target.value)}
            >
              <option value="">请选择右侧档案</option>
              {profiles.map((profile) => (
                <option key={profile.profile_version_id} value={profile.profile_version_id}>
                  {formatProfileOption(profile)}
                </option>
              ))}
            </select>
            <p className={formControls.hint}>
              两侧必须是不同版本；结果只展示四柱比较表和服务端边界说明。
            </p>
          </div>

          {submitError ? <p className={styles.error} role="alert">{submitError}</p> : null}
          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动同盘事实任务，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              开始比较四柱事实{busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
