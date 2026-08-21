"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ButtonLink } from "@/components/button-link";
import {
  formatProfileOption,
  listProfiles,
  startTodayReading,
  startWeekReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

type FortuneFlowProps = {
  mode: "today" | "week";
};

const fortuneSchema = z.object({
  profile_version_id: z.string().min(1, "请选择档案"),
});

type FortuneFormValues = z.infer<typeof fortuneSchema>;

export function FortuneFlow({ mode }: FortuneFlowProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedProfile = searchParams.get("profile");
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const busyRef = useRef(false);
  const intentKeyRef = useRef<IntentKey | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FortuneFormValues>({
    resolver: zodResolver(fortuneSchema),
    defaultValues: { profile_version_id: preselectedProfile ?? "" },
  });

  // 档案异步载入后，若入口带了 ?profile= 则预选对应版本。
  useEffect(() => {
    if (
      !loading &&
      !error &&
      profiles.length > 0 &&
      preselectedProfile &&
      profiles.some((profile) => profile.profile_version_id === preselectedProfile)
    ) {
      setValue("profile_version_id", preselectedProfile);
    }
  }, [loading, error, profiles, preselectedProfile, setValue]);

  useEffect(() => {
    let active = true;
    listProfiles()
      .then((data) => {
        if (!active) return;
        setProfiles(data.profiles);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError("读取失败，请重试");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadAttempt]);

  function retryLoad() {
    setLoading(true);
    setError("");
    setLoadAttempt((attempt) => attempt + 1);
  }

  const handleStart = useCallback(
    async (values: FortuneFormValues) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setSubmitError("");
    const payload = {
      profile_version_id: values.profile_version_id,
      query:
        mode === "today"
          ? "看看今天的事业与工作节奏"
          : "看看近七日的事业与工作节奏",
    };
    const intent = stableKeyForIntent(intentKeyRef.current, payload);
    intentKeyRef.current = intent;
    try {
      const response =
        mode === "today"
          ? await startTodayReading(payload, intent.key)
          : await startWeekReading(payload, intent.key);
      router.push(`/app/readings/${response.reading_version_id}`);
    } catch {
      setSubmitError("读取失败，请重试");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
    },
    [mode, router],
  );

  return (
    <div className={styles.wrap}>
      <h2>开始解读</h2>
      <p className={styles.scopeNotice}>
        <strong>当前算法范围：事业与工作。</strong>
        其他主题还未在今日 / 近七日入口开放，界面不会暗中换范围。
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
          <ButtonLink href="/account/profiles">去建档</ButtonLink>
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
            <label htmlFor="fortune-profile">档案版本</label>
            <select
              id="fortune-profile"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.profile_version_id)}
              aria-describedby={
                errors.profile_version_id
                  ? "fortune-profile-error"
                  : "fortune-profile-help"
              }
              {...register("profile_version_id")}
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
              <p className={formControls.error} id="fortune-profile-error" role="alert">
                {errors.profile_version_id.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="fortune-profile-help">
              请选择已确认的出生档案。
            </p>
          </div>

          {submitError ? (
            <p className={styles.error} role="alert" aria-live="polite">
              {submitError}
            </p>
          ) : null}

          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动解读，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              {mode === "today" ? "开始今日解读" : "开始近七日解读"}
              {busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
