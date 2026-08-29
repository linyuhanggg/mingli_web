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
  startRhythmReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

const rhythmSchema = z.object({
  profile_version_id: z.string().min(1, "请选择档案"),
});

type RhythmFormValues = z.infer<typeof rhythmSchema>;

export function RhythmFactsFlow() {
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
  } = useForm<RhythmFormValues>({
    resolver: zodResolver(rhythmSchema),
    defaultValues: { profile_version_id: preselectedProfile ?? "" },
  });

  useEffect(() => {
    let active = true;
    listProfiles()
      .then((data) => {
        if (!active) return;
        setProfiles(data.profiles);
        if (
          preselectedProfile &&
          data.profiles.some(
            (profile) => profile.profile_version_id === preselectedProfile,
          )
        ) {
          setValue("profile_version_id", preselectedProfile);
        } else if (data.profiles.length === 1) {
          setValue("profile_version_id", data.profiles[0].profile_version_id);
        }
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
  }, [loadAttempt, preselectedProfile, setValue]);

  const handleStart = useCallback(
    async (values: RhythmFormValues) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const payload = {
        profile_version_id: values.profile_version_id,
        query: "只展示四柱纳音对应的本命音律事实",
        dimension_ids: ["state"] as ["state"],
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await startRhythmReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "本命音律任务启动失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [router],
  );

  function retryLoad() {
    setLoading(true);
    setError("");
    setLoadAttempt((attempt) => attempt + 1);
  }

  return (
    <div className={styles.wrap}>
      <h2>查看本命音律事实</h2>
      <p className={styles.lead}>
        从已确认档案读取服务端计算的四柱纳音；本页只展示纳音事实，不把它扩写成姓名学、吉凶或性格结论。
      </p>
      <p className={styles.scopeNotice}>
        <strong>当前输出范围：四柱、纳音、禄命结构事实。</strong>
        音律事实与解释结论分开；浏览器不会自行排盘或重算纳音。
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
          <p>还没有可用的档案。请先建立一份确认的出生资料。</p>
          <ButtonLink href="/account/profiles/new">去建档</ButtonLink>
        </div>
      ) : null}

      {!loading && !error && profiles.length > 0 ? (
        <form
          className={styles.form}
          // eslint-disable-next-line react-hooks/refs -- react-hook-form invokes this only on submit
          onSubmit={handleSubmit(handleStart)}
          noValidate
          aria-busy={busy}
        >
          <div className={formControls.field}>
            <label htmlFor="rhythm-profile">档案版本</label>
            <select
              id="rhythm-profile"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.profile_version_id)}
              aria-describedby={
                errors.profile_version_id
                  ? "rhythm-profile-error"
                  : "rhythm-profile-help"
              }
              {...register("profile_version_id")}
            >
              <option value="">请选择档案</option>
              {profiles.map((profile) => (
                <option key={profile.profile_version_id} value={profile.profile_version_id}>
                  {formatProfileOption(profile)}
                </option>
              ))}
            </select>
            {errors.profile_version_id ? (
              <p className={formControls.error} id="rhythm-profile-error" role="alert">
                {errors.profile_version_id.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="rhythm-profile-help">
              只读取你已确认的 ProfileVersion；不会在 URL 或浏览器中暴露出生资料。
            </p>
          </div>

          {submitError ? <p className={styles.error} role="alert">{submitError}</p> : null}
          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动音律事实任务，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              开始读取音律事实{busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
