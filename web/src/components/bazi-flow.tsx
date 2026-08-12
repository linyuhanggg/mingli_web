"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ButtonLink } from "@/components/button-link";
import { BaziChart } from "@/components/readings/bazi-chart";
import {
  formatProfileOption,
  listProfiles,
  syncBaziChart,
  type BaziChartNeedInputResponse,
  type BaziChartReadyResponse,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";
import { buildBaziChartView } from "@/lib/reading-display";

import styles from "./bazi-flow.module.css";
import formControls from "./form-controls.module.css";

const baziSchema = z.object({
  profile_version_id: z.string().min(1, "请选择档案"),
});

type BaziFormValues = z.infer<typeof baziSchema>;

export function BaziFlow({
  initialProfileVersionId = "",
}: Readonly<{ initialProfileVersionId?: string }>) {
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [chartResult, setChartResult] = useState<BaziChartReadyResponse | null>(
    null,
  );
  const [pendingInput, setPendingInput] =
    useState<BaziChartNeedInputResponse | null>(null);
  const busyRef = useRef(false);
  const intentKeyRef = useRef<IntentKey | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<BaziFormValues>({
    resolver: zodResolver(baziSchema),
    defaultValues: {
      profile_version_id: initialProfileVersionId,
    },
  });
  const profileRegistration = register("profile_version_id");
  const chartView = useMemo(
    () =>
      chartResult
        ? buildBaziChartView(chartResult.fact_panel.facts)
        : null,
    [chartResult],
  );

  useEffect(() => {
    let active = true;
    listProfiles()
      .then((data) => {
        if (!active) return;
        setProfiles(data.profiles);
        if (
          initialProfileVersionId &&
          data.profiles.some(
            (profile) => profile.profile_version_id === initialProfileVersionId,
          )
        ) {
          setValue("profile_version_id", initialProfileVersionId);
        } else if (data.profiles.length === 1) {
          setValue("profile_version_id", data.profiles[0].profile_version_id);
        }
        setLoading(false);
      })
      .catch((reason) => {
        if (!active) return;
        setError(
          reason instanceof Error ? reason.message : "档案加载失败，请稍后重试。",
        );
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [initialProfileVersionId, loadAttempt, setValue]);

  function retryLoad() {
    setLoading(true);
    setError("");
    setLoadAttempt((attempt) => attempt + 1);
  }

  function resetChart() {
    intentKeyRef.current = null;
    setChartResult(null);
    setPendingInput(null);
    setSubmitError("");
  }

  const handleStart = useCallback(
    async (values: BaziFormValues) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const payload = {
        profile_version_id: values.profile_version_id,
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await syncBaziChart(payload, intent.key);
        if (response.status === "ready") {
          setChartResult(response);
          setPendingInput(null);
        } else {
          setChartResult(null);
          setPendingInput(response);
        }
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "同步排盘失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [],
  );

  return (
    <div className={styles.flow}>
      <section className={styles.setup} aria-labelledby="bazi-sync-heading">
        <h2 id="bazi-sync-heading">同步查看八字命盘</h2>
        <p className={styles.lead}>
          选择已确认的档案版本，由服务端 Runtime 5.1 同步准备命盘；浏览器只负责展示，不参与排盘。
        </p>
        <p className={styles.scopeNotice}>
          <strong>事实盘与深度解读分开。</strong>
          本页只展示 Runtime 返回的结构化事实，不创建解读任务，也不消耗解读权益。
        </p>

        {loading ? (
          <p className={styles.status} role="status">
            正在加载档案…
          </p>
        ) : null}

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
            <p>还没有可用的档案。请先建立一份确认的出生资料。</p>
            <ButtonLink href="/app/profile/new">去建档</ButtonLink>
          </div>
        ) : null}

        {!loading && !error && profiles.length > 0 ? (
          <form
            className={styles.form}
            // eslint-disable-next-line react-hooks/refs -- react-hook-form only invokes the handler at submit time, never during render
            onSubmit={handleSubmit(handleStart)}
            noValidate
            aria-busy={busy}
          >
            <div className={formControls.field}>
              <label htmlFor="bazi-profile">档案版本</label>
              <select
                id="bazi-profile"
                className={formControls.input}
                disabled={busy}
                required
                aria-required="true"
                aria-invalid={Boolean(errors.profile_version_id)}
                aria-describedby={
                  errors.profile_version_id
                    ? "bazi-profile-error"
                    : "bazi-profile-help"
                }
                {...profileRegistration}
                onChange={(event) => {
                  void profileRegistration.onChange(event);
                  resetChart();
                }}
              >
                <option value="">请选择档案</option>
                {profiles.map((profile) => (
                  <option
                    key={profile.profile_version_id}
                    value={profile.profile_version_id}
                  >
                    {formatProfileOption(profile)}
                  </option>
                ))}
              </select>
              {errors.profile_version_id ? (
                <p
                  className={formControls.error}
                  id="bazi-profile-error"
                  role="alert"
                >
                  {errors.profile_version_id.message}
                </p>
              ) : null}
              <p className={formControls.hint} id="bazi-profile-help">
                命盘绑定这个档案版本；资料变更后请重新选择新版本排盘。
              </p>
            </div>

            {submitError ? (
              <p className={styles.error} role="alert" aria-live="polite">
                {submitError}
              </p>
            ) : null}

            {busy ? (
              <p className={formControls.disabledReason} role="status">
                Runtime 正在准备命盘，档案选择与操作已暂时锁定。
              </p>
            ) : null}
            <div className={formControls.actions}>
              <button
                className={clsx(formControls.action, formControls.actionPrimary)}
                type="submit"
                disabled={busy}
                aria-busy={busy}
              >
                {busy ? "正在排盘…" : "同步排盘"}
              </button>
            </div>
          </form>
        ) : null}

        {pendingInput ? (
          <p className={styles.status} role="status">
            Runtime 还需要一项结构化资料，补充入口正在准备中。
          </p>
        ) : null}
      </section>

      {chartResult && chartView ? (
        <section className={styles.result} aria-labelledby="bazi-result-heading">
          <header className={styles.resultHeader}>
            <div>
              <p className={styles.eyebrow}>同步事实盘</p>
              <h2 id="bazi-result-heading">命盘已就绪</h2>
            </div>
            <p>未创建解读任务 · 未调用模型 · 未核销权益</p>
          </header>
          <BaziChart chart={chartView} title="本命细盘" />
        </section>
      ) : null}
    </div>
  );
}
