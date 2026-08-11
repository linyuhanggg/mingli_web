"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import {
  appendProfileVersion,
  confirmProfileDraft,
  createProfileDraft,
  type BirthTimeCertainty,
  type Calendar,
  type CoordinatePrecision,
  type CoordinateSource,
  type Gender,
  type TimeBasisPolicy,
  type ZiHourPolicy,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { isIanaTimeZone } from "@/lib/iana-timezones";

import {
  BirthBasisSummary,
  type BirthBasisSummaryValues,
} from "./birth-basis-summary";
import styles from "./profile-form.module.css";
import formControls from "./form-controls.module.css";
import { IanaTimeZoneOptions } from "./iana-timezone-options";

const GENDERS: { value: Gender; label: string }[] = [
  { value: "female", label: "女" },
  { value: "male", label: "男" },
  { value: "other", label: "其他" },
];

const CALENDARS: { value: Calendar; label: string }[] = [
  { value: "gregorian", label: "公历（阳历）" },
  { value: "lunar", label: "农历（阴历）" },
];

const BIRTH_TIME_CERTAINTIES: { value: BirthTimeCertainty; label: string }[] = [
  { value: "exact", label: "时辰准确" },
  { value: "approximate", label: "大概时段" },
  { value: "unknown", label: "无法确定时辰" },
];

const COORDINATE_SOURCES: { value: CoordinateSource; label: string }[] = [
  { value: "user_confirmed", label: "本人按资料逐项确认" },
  { value: "gazetteer", label: "地图或地名库查询" },
];

const COORDINATE_PRECISIONS: { value: CoordinatePrecision; label: string }[] = [
  { value: "exact", label: "精确坐标" },
  { value: "city", label: "城市级" },
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
    calendar: z
      .enum(["", "gregorian", "lunar"])
      .refine((value) => value !== "", "请选择历法"),
    lunar_leap_month: z.boolean().default(false),
    birth_time_certainty: z
      .enum(["", "exact", "approximate", "unknown"])
      .refine((value) => value !== "", "请选择时辰准确度"),
    time_basis_policy: z
      .enum(["", "civil", "solar", "lunar"])
      .refine((value) => value !== "", "请选择时间口径"),
    zi_hour_policy: z
      .enum(["", "midnight", "substitute", "solar"])
      .refine((value) => value !== "", "请选择子时口径"),
    longitude: longitudeField.default(""),
    latitude: latitudeField.default(""),
    coordinate_source: z
      .enum(["", "user_confirmed", "gazetteer"])
      .default(""),
    coordinate_precision: z.enum(["", "exact", "city"]).default(""),
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
    if (data.time_basis_policy !== "solar") {
      return;
    }
    if (data.longitude.trim() === "" || data.latitude.trim() === "") {
      context.addIssue({
        code: "custom",
        message:
          "真太阳时需要逐项确认经纬度、坐标来源与精度；无法确认时请改用其他口径，系统不会静默估算。",
        path: ["longitude"],
      });
    }
    if (data.coordinate_source === "") {
      context.addIssue({
        code: "custom",
        message: "请确认坐标来源",
        path: ["coordinate_source"],
      });
    }
    if (data.coordinate_precision === "") {
      context.addIssue({
        code: "custom",
        message: "请确认坐标精度",
        path: ["coordinate_precision"],
      });
    }
  });

type ProfileFormValues = z.input<typeof profileSchema>;

export function ProfileForm({ editProfileId }: { editProfileId?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const busyRef = useRef(false);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      birth_datetime: "",
      timezone: "Asia/Shanghai",
      location: "",
      gender: "",
      calendar: "",
      lunar_leap_month: false,
      birth_time_certainty: "",
      time_basis_policy: "",
      zi_hour_policy: "",
      longitude: "",
      latitude: "",
      coordinate_source: "",
      coordinate_precision: "",
    },
  });
  const [
    birth_datetime,
    timezone,
    location,
    calendar,
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
      "calendar",
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
        !values.calendar ||
        !values.birth_time_certainty ||
        !values.time_basis_policy ||
        !values.zi_hour_policy
      ) {
        return;
      }
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      try {
        const solar = values.time_basis_policy === "solar";
        const body = {
          birth_datetime: localDateTimeWithOffset(
            values.birth_datetime,
            values.timezone,
          ),
          timezone: values.timezone,
          location: values.location.trim(),
          gender: values.gender,
          calendar: values.calendar,
          lunar_leap_month:
            values.calendar === "lunar"
              ? (values.lunar_leap_month ?? false)
              : false,
          birth_time_certainty: values.birth_time_certainty,
          time_basis_policy: values.time_basis_policy,
          zi_hour_policy: values.zi_hour_policy,
          longitude:
            solar && values.longitude?.trim() !== ""
              ? Number(values.longitude)
              : undefined,
          latitude:
            solar && values.latitude?.trim() !== ""
              ? Number(values.latitude)
              : undefined,
          coordinate_source:
            solar && values.coordinate_source !== ""
              ? values.coordinate_source
              : undefined,
          coordinate_precision:
            solar && values.coordinate_precision !== ""
              ? values.coordinate_precision
              : undefined,
        };
        if (editProfileId) {
          await appendProfileVersion(editProfileId, body);
          router.push("/app/profiles?updated=1");
        } else {
          const draft = await createProfileDraft("本人");
          await confirmProfileDraft(draft.draft_id, body);
          router.push("/app/profiles?created=1");
        }
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "档案保存失败，请稍后重试。",
        );
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [editProfileId, router],
  );

  return (
    <div className={styles.wrap}>
      <h2>{editProfileId ? "修改档案资料" : "建立命理档案"}</h2>
      <p className={styles.lead}>
        {editProfileId
          ? "重新核对出生事实并提交；本次修改会保存为同一档案下的新不可变版本，历史版本与既有解读不受影响。"
          : "这里只记录出生事实，不进行任何本地推算。"}
      </p>

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

          <div className={formControls.field}>
            <label htmlFor="profile-calendar">历法</label>
            <select
              id="profile-calendar"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.calendar)}
              aria-describedby={
                errors.calendar
                  ? "profile-calendar-error"
                  : "profile-calendar-help"
              }
              {...register("calendar")}
            >
              <option value="" disabled>
                请选择历法
              </option>
              {CALENDARS.map((calendar) => (
                <option key={calendar.value} value={calendar.value}>
                  {calendar.label}
                </option>
              ))}
            </select>
            {errors.calendar ? (
              <p
                className={formControls.error}
                id="profile-calendar-error"
                role="alert"
              >
                {errors.calendar.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-calendar-help">
              上方出生时间按所选历法记录；农历由服务端换算，不做本地推算。
            </p>
          </div>

          {calendar === "lunar" ? (
            <div className={formControls.field}>
              <label htmlFor="profile-lunar-leap-month">闰月</label>
              <input
                id="profile-lunar-leap-month"
                type="checkbox"
                disabled={busy}
                aria-describedby="profile-lunar-leap-month-help"
                {...register("lunar_leap_month")}
              />
              <p className={formControls.hint} id="profile-lunar-leap-month-help">
                仅当出生月份是农历闰月时勾选；不确定请不要勾选，并在时辰准确度中说明。
              </p>
            </div>
          ) : null}

          <div className={formControls.field}>
            <label htmlFor="profile-birth-time-certainty">时辰准确度</label>
            <select
              id="profile-birth-time-certainty"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.birth_time_certainty)}
              aria-describedby={
                errors.birth_time_certainty
                  ? "profile-birth-time-certainty-error"
                  : "profile-birth-time-certainty-help"
              }
              {...register("birth_time_certainty")}
            >
              <option value="" disabled>
                请选择时辰准确度
              </option>
              {BIRTH_TIME_CERTAINTIES.map((certainty) => (
                <option key={certainty.value} value={certainty.value}>
                  {certainty.label}
                </option>
              ))}
            </select>
            {errors.birth_time_certainty ? (
              <p
                className={formControls.error}
                id="profile-birth-time-certainty-error"
                role="alert"
              >
                {errors.birth_time_certainty.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="profile-birth-time-certainty-help">
              无法确定时辰时，解读会明确标注这一不确定性，而不是假装精确。
            </p>
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
            <label htmlFor="profile-longitude">经度</label>
            <input
              id="profile-longitude"
              className={formControls.input}
              type="number"
              step="any"
              inputMode="decimal"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
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
            <label htmlFor="profile-latitude">纬度</label>
            <input
              id="profile-latitude"
              className={formControls.input}
              type="number"
              step="any"
              inputMode="decimal"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
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
            <label htmlFor="profile-coordinate-source">坐标来源</label>
            <select
              id="profile-coordinate-source"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.coordinate_source)}
              aria-describedby={
                errors.coordinate_source
                  ? "profile-coordinate-source-error"
                  : undefined
              }
              {...register("coordinate_source")}
            >
              <option value="" disabled>
                请选择坐标来源
              </option>
              {COORDINATE_SOURCES.map((source) => (
                <option key={source.value} value={source.value}>
                  {source.label}
                </option>
              ))}
            </select>
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

          <div className={formControls.field}>
            <label htmlFor="profile-coordinate-precision">坐标精度</label>
            <select
              id="profile-coordinate-precision"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.coordinate_precision)}
              aria-describedby={
                errors.coordinate_precision
                  ? "profile-coordinate-precision-error"
                  : undefined
              }
              {...register("coordinate_precision")}
            >
              <option value="" disabled>
                请选择坐标精度
              </option>
              {COORDINATE_PRECISIONS.map((precision) => (
                <option key={precision.value} value={precision.value}>
                  {precision.label}
                </option>
              ))}
            </select>
            {errors.coordinate_precision ? (
              <p
                className={formControls.error}
                id="profile-coordinate-precision-error"
                role="alert"
              >
                {errors.coordinate_precision.message}
              </p>
            ) : null}
          </div>
            </>
          ) : null}
          </div>
          <p className={styles.policyNote}>
            只有选择真太阳时，才需要逐项确认经纬度、坐标来源与精度；其他口径不会提交这些高级字段。坐标无法确认时请改用其他口径，系统不会静默估算。
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
