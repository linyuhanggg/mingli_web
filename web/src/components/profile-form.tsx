"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  confirmProfileDraft,
  createProfileDraft,
  type Gender,
  type TimeBasisPolicy,
  type ZiHourPolicy,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";

import styles from "./profile-form.module.css";

const TIMEZONES = [
  "Asia/Shanghai",
  "Asia/Hong_Kong",
  "Asia/Tokyo",
  "Europe/London",
  "America/New_York",
  "UTC",
] as const;

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

const profileSchema = z.object({
  birth_datetime: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/, "请填写出生时间"),
  timezone: z.string().min(1, "请选择出生时区"),
  location: z.string().trim().min(1, "请填写出生地点"),
  gender: z.enum(["female", "male", "other"]),
  time_basis_policy: z.enum(["civil", "solar", "lunar"]),
  zi_hour_policy: z.enum(["midnight", "substitute", "solar"]),
  longitude: longitudeField.default(""),
  latitude: latitudeField.default(""),
  coordinate_source: z.string().trim().default(""),
});

type ProfileFormValues = z.input<typeof profileSchema>;

export function ProfileForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const busyRef = useRef(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      birth_datetime: "",
      timezone: "Asia/Shanghai",
      location: "",
      gender: "female",
      time_basis_policy: "civil",
      zi_hour_policy: "midnight",
      longitude: "",
      latitude: "",
      coordinate_source: "",
    },
  });

  const handleSave = useCallback(
    async (values: ProfileFormValues) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setSubmitError("");
    try {
      const draft = await createProfileDraft("本人");
      await confirmProfileDraft(draft.draft_id, {
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
          values.longitude?.trim() === "" ? undefined : Number(values.longitude),
        latitude:
          values.latitude?.trim() === "" ? undefined : Number(values.latitude),
        coordinate_source:
          values.coordinate_source?.trim() === ""
            ? undefined
            : values.coordinate_source?.trim(),
      });
      router.push("/app");
    } catch (reason) {
      setSubmitError(
        reason instanceof Error ? reason.message : "档案保存失败，请稍后重试。",
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
      <h1>建立命理档案</h1>
      <p className={styles.lead}>这里只记录出生事实，不进行任何本地推算。</p>

      {submitError ? (
        <p className={styles.errorBox} role="alert" aria-live="polite">
          {submitError}
        </p>
      ) : null}

      <form
        className={styles.form}
        // eslint-disable-next-line react-hooks/refs -- react-hook-form only invokes the handler at submit time, never during render
        onSubmit={handleSubmit(handleSave)}
        noValidate
        aria-busy={busy}
      >
        <div className={styles.grid}>
          <div className={styles.field}>
            <label htmlFor="profile-birth-datetime">出生时间</label>
            <input
              id="profile-birth-datetime"
              type="datetime-local"
              step="1"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.birth_datetime)}
              aria-describedby={
                errors.birth_datetime ? "profile-birth-datetime-error" : undefined
              }
              {...register("birth_datetime")}
            />
            {errors.birth_datetime ? (
              <p
                className={styles.fieldError}
                id="profile-birth-datetime-error"
                role="alert"
              >
                {errors.birth_datetime.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-timezone">出生时区</label>
            <select
              id="profile-timezone"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.timezone)}
              aria-describedby={
                errors.timezone ? "profile-timezone-error" : undefined
              }
              {...register("timezone")}
            >
              {TIMEZONES.map((timezone) => (
                <option key={timezone} value={timezone}>
                  {timezone}
                </option>
              ))}
            </select>
            {errors.timezone ? (
              <p className={styles.fieldError} id="profile-timezone-error" role="alert">
                {errors.timezone.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-location">出生地点</label>
            <input
              id="profile-location"
              type="text"
              autoComplete="address-level2"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.location)}
              aria-describedby={
                errors.location ? "profile-location-error" : undefined
              }
              {...register("location")}
            />
            {errors.location ? (
              <p className={styles.fieldError} id="profile-location-error" role="alert">
                {errors.location.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-gender">性别</label>
            <select
              id="profile-gender"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.gender)}
              aria-describedby={
                errors.gender ? "profile-gender-error" : undefined
              }
              {...register("gender")}
            >
              {GENDERS.map((gender) => (
                <option key={gender.value} value={gender.value}>
                  {gender.label}
                </option>
              ))}
            </select>
            {errors.gender ? (
              <p className={styles.fieldError} id="profile-gender-error" role="alert">
                {errors.gender.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-time-basis-policy">时间口径</label>
            <select
              id="profile-time-basis-policy"
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
              {TIME_BASIS_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {policy.label}
                </option>
              ))}
            </select>
            {errors.time_basis_policy ? (
              <p
                className={styles.fieldError}
                id="profile-time-basis-policy-error"
                role="alert"
              >
                {errors.time_basis_policy.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-zi-hour-policy">子时口径</label>
            <select
              id="profile-zi-hour-policy"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.zi_hour_policy)}
              aria-describedby={
                errors.zi_hour_policy ? "profile-zi-hour-policy-error" : undefined
              }
              {...register("zi_hour_policy")}
            >
              {ZI_HOUR_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {policy.label}
                </option>
              ))}
            </select>
            {errors.zi_hour_policy ? (
              <p
                className={styles.fieldError}
                id="profile-zi-hour-policy-error"
                role="alert"
              >
                {errors.zi_hour_policy.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-longitude">经度（可选）</label>
            <input
              id="profile-longitude"
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
              <p className={styles.fieldError} id="profile-longitude-error" role="alert">
                {errors.longitude.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-latitude">纬度（可选）</label>
            <input
              id="profile-latitude"
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
              <p className={styles.fieldError} id="profile-latitude-error" role="alert">
                {errors.latitude.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="profile-coordinate-source">坐标来源（可选）</label>
            <input
              id="profile-coordinate-source"
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
                className={styles.fieldError}
                id="profile-coordinate-source-error"
                role="alert"
              >
                {errors.coordinate_source.message}
              </p>
            ) : null}
          </div>
        </div>

        <button
          className={styles.submit}
          type="submit"
          disabled={busy}
          aria-busy={busy}
        >
          保存档案{busy ? " · 正在保存…" : ""}
        </button>
      </form>
    </div>
  );
}
