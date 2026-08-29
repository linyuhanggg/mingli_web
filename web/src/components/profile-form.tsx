"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import {
  confirmProfileDraft,
  createProfileDraft,
  discardProfileDraft,
  type Gender,
  type ProfileConfirmRequest,
  type TimeBasisPolicy,
  type ZiHourPolicy,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { isIanaTimeZone } from "@/lib/iana-timezones";
import {
  isProfileNameConflict,
  readProfileNameConflict,
  type ProfileNameConflict,
} from "@/lib/profile-conflict";

import {
  BirthBasisSummary,
  type BirthBasisSummaryValues,
} from "./birth-basis-summary";
import { ProfileNameConflictDialog } from "./profile-name-conflict-dialog";
import styles from "./profile-form.module.css";
import formControls from "./form-controls.module.css";
import { IanaTimeZoneOptions } from "./iana-timezone-options";

const GENDERS: { value: Gender; label: string }[] = [
  { value: "female", label: "女" },
  { value: "male", label: "男" },
  { value: "other", label: "其他" },
];

const TIME_BASIS_POLICIES: { value: TimeBasisPolicy; label: string }[] = [
  { value: "civil", label: "民用时" },
  { value: "solar", label: "真太阳时" },
  { value: "lunar", label: "农历时间口径" },
];

const ZI_HOUR_POLICIES: { value: ZiHourPolicy; label: string }[] = [
  { value: "midnight", label: "按午夜换日" },
  { value: "substitute", label: "子时替代口径" },
  { value: "solar", label: "按太阳时判断子时" },
];

const longitudeField = z
  .string()
  .trim()
  .refine(
    (value) =>
      value === "" ||
      (Number.isFinite(Number(value)) && Number(value) >= -180 && Number(value) <= 180),
    "请输入 -180 到 180 之间的经度",
  );

const latitudeField = z
  .string()
  .trim()
  .refine(
    (value) =>
      value === "" ||
      (Number.isFinite(Number(value)) && Number(value) >= -90 && Number(value) <= 90),
    "请输入 -90 到 90 之间的纬度",
  );

const profileSchema = z
  .object({
    display_name: z.string().trim().max(80, "名称最多 80 个字").default(""),
    birth_datetime: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/, "请填写出生时间"),
    timezone: z.string(),
    location: z
      .string()
      .trim()
      .min(1, "请填写出生地点")
      .max(80, "地点最多 80 个字"),
    gender: z
      .enum(["", "female", "male", "other"])
      .refine((value) => value !== "", "请选择性别"),
    time_basis_policy: z
      .enum(["", "civil", "solar", "lunar"])
      .refine((value) => value !== "", "请选择时间口径"),
    zi_hour_policy: z
      .enum(["", "midnight", "substitute", "solar"])
      .refine((value) => value !== "", "请选择子时口径"),
    longitude: longitudeField.default(""),
    latitude: latitudeField.default(""),
    coordinate_source: z
      .string()
      .trim()
      .max(40, "坐标来源最多 40 个字")
      .default(""),
  })
  .superRefine((data, context) => {
    if (!data.timezone) {
      context.addIssue({
        code: "custom",
        message: "请选择出生时区",
        path: ["timezone"],
      });
    } else if (!isIanaTimeZone(data.timezone)) {
      context.addIssue({
        code: "custom",
        message: "请选择列表中的有效 IANA 时区",
        path: ["timezone"],
      });
    }
  });

type ProfileFormValues = z.input<typeof profileSchema>;

function confirmedProfileHref(profile: {
  profile_id: string;
  profile_version_id: string;
}): string {
  return `/account/profiles/${encodeURIComponent(profile.profile_id)}?version=${encodeURIComponent(profile.profile_version_id)}`;
}

export function ProfileForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [nameConflict, setNameConflict] = useState<ProfileNameConflict | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<{
    draftId: string;
    body: ProfileConfirmRequest;
    formSnapshot: string;
  } | null>(null);
  const busyRef = useRef(false);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      display_name: "",
      birth_datetime: "",
      timezone: "Asia/Shanghai",
      location: "",
      gender: "",
      time_basis_policy: "",
      zi_hour_policy: "",
      longitude: "",
      latitude: "",
      coordinate_source: "",
    },
  });
  const [
    birth_datetime,
    timezone,
    location,
    time_basis_policy,
    zi_hour_policy,
    longitude,
    latitude,
  ] = useWatch({
    control,
    name: [
      "birth_datetime",
      "timezone",
      "location",
      "time_basis_policy",
      "zi_hour_policy",
      "longitude",
      "latitude",
    ],
  });
  const watchedValues: BirthBasisSummaryValues = {
    birth_datetime,
    timezone,
    location,
    time_basis_policy,
    zi_hour_policy,
    longitude,
    latitude,
  };

  const handleSave = useCallback(
    async (values: ProfileFormValues) => {
      if (busyRef.current) return;
      if (
        !values.gender ||
        !values.time_basis_policy ||
        !values.zi_hour_policy
      ) {
        return;
      }
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      setNameConflict(null);
      let pending = pendingConfirm;
      try {
        const displayName = values.display_name?.trim() || undefined;
        const body: ProfileConfirmRequest = {
          birth_datetime: localDateTimeWithOffset(
            values.birth_datetime,
            values.timezone,
          ),
          timezone: values.timezone,
          location: values.location.trim(),
          gender: values.gender,
          time_basis_policy: values.time_basis_policy,
          zi_hour_policy: values.zi_hour_policy,
          longitude:
            values.time_basis_policy !== "solar" ||
            values.longitude?.trim() === ""
              ? undefined
              : Number(values.longitude),
          latitude:
            values.time_basis_policy !== "solar" ||
            values.latitude?.trim() === ""
              ? undefined
              : Number(values.latitude),
          coordinate_source:
            values.time_basis_policy !== "solar" ||
            values.coordinate_source?.trim() === ""
              ? undefined
              : values.coordinate_source?.trim(),
          on_name_conflict: "reject",
        };
        const formSnapshot = JSON.stringify({
          displayName: displayName ?? null,
          body,
        });
        if (pending && pending.formSnapshot !== formSnapshot) {
          await discardProfileDraft(pending.draftId);
          setPendingConfirm(null);
          pending = null;
        }
        if (!pending) {
          const draft = await createProfileDraft(displayName);
          pending = { draftId: draft.draft_id, body, formSnapshot };
          setPendingConfirm(pending);
        }
        await confirmProfileDraft(pending.draftId, pending.body);
        setPendingConfirm(null);
        router.push("/account/profiles?created=1");
      } catch (reason) {
        if (isProfileNameConflict(reason)) {
          setNameConflict(readProfileNameConflict(reason));
        } else {
          const message =
            reason instanceof Error ? reason.message : "档案保存失败，请稍后重试。";
          setSubmitError(
            pending
              ? `${message} 未确认草稿已保留；重试不会创建新草稿。如需按当前表单重建，请先放弃草稿。`
              : message,
          );
        }
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [pendingConfirm, router],
  );

  const resolveConflict = useCallback(
    async (action: "overwrite" | "save_as") => {
      const pending = pendingConfirm;
      if (!pending || busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      try {
        const profile = await confirmProfileDraft(pending.draftId, {
          ...pending.body,
          on_name_conflict: action,
        });
        setPendingConfirm(null);
        setNameConflict(null);
        router.push(confirmedProfileHref(profile));
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "档案保存失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [pendingConfirm, router],
  );

  const discardPendingDraft = useCallback(async () => {
    const pending = pendingConfirm;
    if (!pending) {
      setNameConflict(null);
      return;
    }
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setSubmitError("");
    try {
      await discardProfileDraft(pending.draftId);
      setPendingConfirm(null);
      setNameConflict(null);
    } catch (reason) {
      setSubmitError(
        reason instanceof Error ? reason.message : "未能删除未确认草稿，请稍后重试。",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }, [pendingConfirm]);

  return (
    <div className={styles.wrap}>
      <h2>建立命理档案</h2>
      <p className={styles.lead}>这里只记录出生事实，不进行任何本地推算。名称可留空，由服务端生成回退名。</p>
      <ProfileNameConflictDialog
        conflict={nameConflict}
        busy={busy}
        onOverwrite={() => void resolveConflict("overwrite")}
        onSaveAs={() => void resolveConflict("save_as")}
        onCancel={() => {
          void discardPendingDraft();
        }}
      />

      {submitError ? (
        <p className={styles.errorBox} role="alert" aria-live="polite">
          {submitError}
        </p>
      ) : null}
      {submitError && pendingConfirm && !nameConflict ? (
        <div className={formControls.actions} role="group" aria-label="未确认草稿操作">
          <button
            className={clsx(formControls.action, formControls.actionSecondary)}
            disabled={busy}
            onClick={() => void handleSubmit(handleSave)()}
            type="button"
          >
            重试确认
          </button>
          <button
            className={clsx(formControls.action, formControls.actionSecondary)}
            disabled={busy}
            onClick={() => void discardPendingDraft()}
            type="button"
          >
            放弃未确认草稿
          </button>
        </div>
      ) : null}

      <form
        className={styles.form}
        // eslint-disable-next-line react-hooks/refs -- react-hook-form only invokes the handler at submit time, never during render
        onSubmit={handleSubmit(handleSave)}
        noValidate
        aria-busy={busy}
      >
        <section className={styles.step} aria-labelledby="profile-step-facts">
          <div className={styles.stepHeader}>
            <span className={styles.stepIndex} aria-hidden="true">01</span>
            <div>
              <h3 id="profile-step-facts">1. 出生事实</h3>
              <p>先填写原始资料。这里不做换算，也不会读取设备定位。</p>
            </div>
          </div>
          <div className={styles.grid}>
          <div className={formControls.field}>
            <label htmlFor="profile-display-name">档案名称（可选）</label>
            <input
              id="profile-display-name"
              className={formControls.input}
              autoComplete="nickname"
              disabled={busy}
              placeholder="留空则使用服务端回退名"
              {...register("display_name")}
            />
            {errors.display_name ? (
              <p className={formControls.error} role="alert">
                {errors.display_name.message}
              </p>
            ) : (
              <p className={formControls.hint}>可不填。保存后可在档案列表重命名。</p>
            )}
          </div>
          <div className={formControls.field}>
            <label htmlFor="profile-birth-datetime">出生时间</label>
            <input
              id="profile-birth-datetime"
              className={formControls.input}
              type="datetime-local"
              step="1"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.birth_datetime)}
              aria-describedby={
                errors.birth_datetime
                  ? "profile-birth-datetime-error"
                  : "profile-birth-datetime-help"
              }
              {...register("birth_datetime")}
            />
            {errors.birth_datetime ? (
              <p
                className={formControls.error}
                id="profile-birth-datetime-error"
                role="alert"
              >
                {errors.birth_datetime.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-birth-datetime-help">
              只记录出生地钟表时间；与所选时区配对后，由服务端规范化。
            </p>
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-timezone">出生时区</label>
            <input
              id="profile-timezone"
              className={formControls.input}
              type="text"
              inputMode="text"
              autoComplete="off"
              spellCheck="false"
              list="profile-timezone-options"
              placeholder="输入并选择，例如 Asia/Shanghai…"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.timezone)}
              aria-describedby={
                errors.timezone ? "profile-timezone-error" : "profile-timezone-help"
              }
              {...register("timezone")}
            />
            <IanaTimeZoneOptions id="profile-timezone-options" />
            {errors.timezone ? (
              <p
                className={formControls.error}
                id="profile-timezone-error"
                role="alert"
              >
                {errors.timezone.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-timezone-help">
              按出生城市主动确认；输入地区或城市可筛选完整 IANA 列表，界面不会读取设备时区。
            </p>
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-location">出生地点</label>
            <input
              id="profile-location"
              className={formControls.input}
              type="text"
              autoComplete="address-level2"
              placeholder="例如：浙江省杭州市…"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.location)}
              aria-describedby={
                errors.location ? "profile-location-error" : "profile-location-help"
              }
              {...register("location")}
            />
            {errors.location ? (
              <p className={formControls.error} id="profile-location-error" role="alert">
                {errors.location.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-location-help">
              城市级信息用于确认时区与口径，不自动索取精确定位。
            </p>
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-gender">性别</label>
            <select
              id="profile-gender"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.gender)}
              aria-describedby={
                errors.gender ? "profile-gender-error" : undefined
              }
              {...register("gender")}
            >
              <option value="" disabled>
                请选择性别
              </option>
              {GENDERS.map((gender) => (
                <option key={gender.value} value={gender.value}>
                  {gender.label}
                </option>
              ))}
            </select>
            {errors.gender ? (
              <p className={formControls.error} id="profile-gender-error" role="alert">
                {errors.gender.message}
              </p>
            ) : null}
          </div>
          </div>
        </section>

        <section className={styles.step} aria-labelledby="profile-step-policy">
          <div className={styles.stepHeader}>
            <span className={styles.stepIndex} aria-hidden="true">02</span>
            <div>
              <h3 id="profile-step-policy">2. 计算口径</h3>
              <p>这些选择会改变服务端算法输入，因此需要你逐项确认。</p>
            </div>
          </div>
          <div className={styles.grid}>
          <div className={formControls.field}>
            <label htmlFor="profile-time-basis-policy">时间口径</label>
            <select
              id="profile-time-basis-policy"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.time_basis_policy)}
              aria-describedby={
                errors.time_basis_policy
                  ? "profile-time-basis-policy-error"
                  : undefined
              }
              {...register("time_basis_policy")}
            >
              <option value="" disabled>
                请选择时间口径
              </option>
              {TIME_BASIS_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {policy.label}
                </option>
              ))}
            </select>
            {errors.time_basis_policy ? (
              <p
                className={formControls.error}
                id="profile-time-basis-policy-error"
                role="alert"
              >
                {errors.time_basis_policy.message}
              </p>
            ) : null}
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-zi-hour-policy">子时口径</label>
            <select
              id="profile-zi-hour-policy"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.zi_hour_policy)}
              aria-describedby={
                errors.zi_hour_policy
                  ? "profile-zi-hour-policy-error"
                  : "profile-zi-hour-policy-help"
              }
              {...register("zi_hour_policy")}
            >
              <option value="" disabled>
                请选择子时口径
              </option>
              {ZI_HOUR_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {policy.label}
                </option>
              ))}
            </select>
            {errors.zi_hour_policy ? (
              <p
                className={formControls.error}
                id="profile-zi-hour-policy-error"
                role="alert"
              >
                {errors.zi_hour_policy.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-zi-hour-policy-help">
              换日策略决定 23:00–23:59 的日柱归属与子时起算口径，请按原始资料确认。
            </p>
          </div>

          {time_basis_policy === "solar" ? (
            <>
          <div className={formControls.field}>
            <label htmlFor="profile-longitude">经度（可选）</label>
            <input
              id="profile-longitude"
              className={formControls.input}
              type="number"
              step="any"
              inputMode="decimal"
              autoComplete="off"
              disabled={busy}
              aria-invalid={Boolean(errors.longitude)}
              aria-describedby={
                errors.longitude ? "profile-longitude-error" : undefined
              }
              {...register("longitude")}
            />
            {errors.longitude ? (
              <p className={formControls.error} id="profile-longitude-error" role="alert">
                {errors.longitude.message}
              </p>
            ) : null}
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-latitude">纬度（可选）</label>
            <input
              id="profile-latitude"
              className={formControls.input}
              type="number"
              step="any"
              inputMode="decimal"
              autoComplete="off"
              disabled={busy}
              aria-invalid={Boolean(errors.latitude)}
              aria-describedby={
                errors.latitude ? "profile-latitude-error" : undefined
              }
              {...register("latitude")}
            />
            {errors.latitude ? (
              <p className={formControls.error} id="profile-latitude-error" role="alert">
                {errors.latitude.message}
              </p>
            ) : null}
          </div>

          <div className={formControls.field}>
            <label htmlFor="profile-coordinate-source">坐标来源（可选）</label>
            <input
              id="profile-coordinate-source"
              className={formControls.input}
              type="text"
              autoComplete="off"
              disabled={busy}
              aria-invalid={Boolean(errors.coordinate_source)}
              aria-describedby={
                errors.coordinate_source
                  ? "profile-coordinate-source-error"
                  : undefined
              }
              {...register("coordinate_source")}
            />
            {errors.coordinate_source ? (
              <p
                className={formControls.error}
                id="profile-coordinate-source-error"
                role="alert"
              >
                {errors.coordinate_source.message}
              </p>
            ) : null}
          </div>
            </>
          ) : null}
          </div>
          <p className={styles.policyNote}>
            只有选择真太阳时，才需要展开经纬度校准；其他口径不会提交这些高级字段。
          </p>
        </section>

        <section className={styles.step} aria-labelledby="profile-step-review">
          <div className={styles.stepHeader}>
            <span className={styles.stepIndex} aria-hidden="true">03</span>
            <div>
              <h3 id="profile-step-review">3. 提交前核对</h3>
              <p>保存后形成不可变档案版本；以后修改会保留旧版本。</p>
            </div>
          </div>
          <BirthBasisSummary values={watchedValues} />
        </section>

        {busy ? (
          <p className={formControls.disabledReason} role="status">
            正在保存，输入与操作已暂时锁定，避免重复提交。
          </p>
        ) : null}
        <div className={formControls.actions}>
          <button
            className={clsx(formControls.action, formControls.actionPrimary)}
            type="submit"
            disabled={busy}
            aria-busy={busy}
          >
            保存档案{busy ? " · 正在保存…" : ""}
          </button>
        </div>
      </form>
    </div>
  );
}
