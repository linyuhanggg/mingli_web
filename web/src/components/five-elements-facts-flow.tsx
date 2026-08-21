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
  startFiveElementsFactsReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

const factsSchema = z.object({
  profile_version_id: z.string().min(1, "请选择档案"),
});

type FactsFormValues = z.infer<typeof factsSchema>;

export function FiveElementsFactsFlow() {
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
  } = useForm<FactsFormValues>({
    resolver: zodResolver(factsSchema),
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
    async (values: FactsFormValues) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const payload = {
        profile_version_id: values.profile_version_id,
        query: "只展示五行库存、季节气候与调候适用性事实",
        dimension_ids: ["state"] as ["state"],
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await startFiveElementsFactsReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "五行事实任务启动失败，请稍后重试。",
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
      <h2>查看五行事实与调候依据</h2>
      <p className={styles.lead}>
        从已确认档案版本出发，读取服务端的五行库存、季节画像和调候适用性身份。
      </p>
      <p className={styles.scopeNotice}>
        <strong>当前只展示事实。旺衰、喜忌、用神没有可展示的结论。</strong>
        五行计数不等于力量裁决；调候标记也不会单独生成用神判断。
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
          <ButtonLink href="/account/profiles">去建档</ButtonLink>
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
            <label htmlFor="five-elements-profile">档案版本</label>
            <select
              id="five-elements-profile"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.profile_version_id)}
              aria-describedby={
                errors.profile_version_id
                  ? "five-elements-profile-error"
                  : "five-elements-profile-help"
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
              <p className={formControls.error} id="five-elements-profile-error" role="alert">
                {errors.profile_version_id.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="five-elements-profile-help">
              只读取你已确认的 ProfileVersion；不会在浏览器重新排盘或用名称替代档案。
            </p>
          </div>

          {submitError ? <p className={styles.error} role="alert">{submitError}</p> : null}
          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动事实任务，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              开始读取事实{busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
