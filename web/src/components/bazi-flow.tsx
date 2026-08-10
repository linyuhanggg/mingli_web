"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ButtonLink } from "@/components/button-link";
import {
  formatProfileOption,
  listProfiles,
  startPreviewReading,
  type ProfileSummary,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

const baziSchema = z.object({
  profile_version_id: z.string().min(1, "请选择档案"),
});

type BaziFormValues = z.infer<typeof baziSchema>;

export function BaziFlow({
  initialProfileVersionId = "",
}: Readonly<{ initialProfileVersionId?: string }>) {
  const router = useRouter();
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
  } = useForm<BaziFormValues>({
    resolver: zodResolver(baziSchema),
    defaultValues: { profile_version_id: initialProfileVersionId },
  });

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

  const handleStart = useCallback(
    async (values: BaziFormValues) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const payload = {
        profile_version_id: values.profile_version_id,
        query: "看一下这个八字",
        dimension_ids: ["career"] as ("overview" | "career")[],
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await startPreviewReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "八字概览启动失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [router],
  );

  return (
    <div className={styles.wrap}>
      <h2>查看八字概览</h2>
      <p className={styles.lead}>
        从已确认档案版本出发，发起确定性八字概览。结果由服务端计算与交付，不在本页本地推算。
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
              <p className={formControls.error} id="bazi-profile-error" role="alert">
                {errors.profile_version_id.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="bazi-profile-help">
              八字概览绑定该档案版本；修改资料会生成新版本，旧解读仍可回看。
            </p>
          </div>

          {submitError ? (
            <p className={styles.error} role="alert" aria-live="polite">
              {submitError}
            </p>
          ) : null}

          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动八字概览，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              开始八字概览{busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
