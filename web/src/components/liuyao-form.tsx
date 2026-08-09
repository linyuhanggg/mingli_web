"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import {
  getCsrfToken,
  startLiuyaoReading,
  type LiuyaoStartRequest,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./liuyao-form.module.css";

const TIMEZONES = [
  "Asia/Shanghai",
  "Asia/Hong_Kong",
  "Asia/Tokyo",
  "Europe/London",
  "America/New_York",
  "UTC",
] as const;

const tossKeys = [
  "toss_1",
  "toss_2",
  "toss_3",
  "toss_4",
  "toss_5",
  "toss_6",
] as const;

const tossNames = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"] as const;

const localDateTimePattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/;

const liuyaoSchema = z
  .object({
    question: z.string().trim().min(2, "请至少输入两个字，把问题想清楚"),
    event_datetime: z
      .string()
      .regex(localDateTimePattern, "请确认起卦时刻"),
    timezone: z.string().min(1, "请选择起卦时区"),
    location: z.string().trim().min(1, "请填写起卦地点"),
    cast_mode: z.enum(["manual", "digital_coin"]),
    toss_1: z.string().default(""),
    toss_2: z.string().default(""),
    toss_3: z.string().default(""),
    toss_4: z.string().default(""),
    toss_5: z.string().default(""),
    toss_6: z.string().default(""),
  })
  .superRefine((value, ctx) => {
    if (value.cast_mode !== "manual") return;
    tossKeys.forEach((key, index) => {
      const toss = value[key];
      if (toss !== "6" && toss !== "7" && toss !== "8" && toss !== "9") {
        ctx.addIssue({
          code: "custom",
          path: [key],
          message: `请选择${tossNames[index]}`,
        });
      }
    });
  });

type LiuyaoFormValues = z.input<typeof liuyaoSchema>;

export function LiuyaoForm() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [bootstrapError, setBootstrapError] = useState("");
  const [bootstrapAttempt, setBootstrapAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const busyRef = useRef(false);
  const intentKeyRef = useRef<IntentKey | null>(null);
  const {
    register,
    handleSubmit,
    control,
    clearErrors,
    formState: { errors },
  } = useForm<LiuyaoFormValues>({
    resolver: zodResolver(liuyaoSchema),
    defaultValues: {
      question: "",
      event_datetime: "",
      timezone: "Asia/Shanghai",
      location: "",
      cast_mode: "manual",
      toss_1: "",
      toss_2: "",
      toss_3: "",
      toss_4: "",
      toss_5: "",
      toss_6: "",
    },
  });
  const castMode = useWatch({ control, name: "cast_mode" });

  useEffect(() => {
    let active = true;
    getCsrfToken()
      .then(() => {
        if (!active) return;
        setReady(true);
        setBootstrapError("");
      })
      .catch((reason) => {
        if (!active) return;
        setBootstrapError(
          reason instanceof Error
            ? reason.message
            : "安全会话建立失败，请重新连接。",
        );
      });
    return () => {
      active = false;
    };
  }, [bootstrapAttempt]);

  useEffect(() => {
    if (castMode !== "manual") {
      clearErrors([...tossKeys]);
    }
  }, [castMode, clearErrors]);

  const handleStart = useCallback(
    async (values: LiuyaoFormValues) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setSubmitError("");

    const cast: LiuyaoStartRequest["cast"] =
      values.cast_mode === "digital_coin"
        ? "digital_coin"
        : (tossKeys.map((key) => Number(values[key])) as [
            number,
            number,
            number,
            number,
            number,
            number,
          ]);
    const payload: LiuyaoStartRequest = {
      cast,
      event_datetime: localDateTimeWithOffset(
        values.event_datetime,
        values.timezone,
      ),
      timezone: values.timezone,
      location: values.location.trim(),
      query: values.question.trim(),
    };
    const intent = stableKeyForIntent(intentKeyRef.current, payload);
    intentKeyRef.current = intent;

    try {
      const response = await startLiuyaoReading(payload, intent.key);
      router.push(`/app/readings/${response.reading_version_id}`);
    } catch (reason) {
      setSubmitError(
        reason instanceof Error ? reason.message : "解读启动失败，请稍后重试。",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
    },
    [router],
  );

  function retryBootstrap() {
    setReady(false);
    setBootstrapError("");
    setBootstrapAttempt((attempt) => attempt + 1);
  }

  return (
    <div className={styles.wrap}>
      <h1>一事一问 · 六爻</h1>
      <p className={styles.lead}>
        把问题想清楚，再确认起卦事实。浏览器只收集输入，不计算卦象。
      </p>

      {!ready && !bootstrapError ? (
        <p className={styles.status} role="status" aria-live="polite">
          正在建立安全会话…
        </p>
      ) : null}

      {bootstrapError ? (
        <div className={styles.state} role="alert">
          <p className={styles.error}>{bootstrapError}</p>
          <button className={styles.secondary} type="button" onClick={retryBootstrap}>
            重新连接
          </button>
        </div>
      ) : null}

      {ready ? (
        <form
          className={styles.form}
          // eslint-disable-next-line react-hooks/refs -- react-hook-form only invokes the handler at submit time, never during render
          onSubmit={handleSubmit(handleStart)}
          noValidate
          aria-busy={busy}
        >
          <div className={styles.field}>
            <label htmlFor="liuyao-question">想清楚问什么</label>
            <textarea
              id="liuyao-question"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.question)}
              aria-describedby={
                errors.question ? "liuyao-question-error" : "liuyao-question-hint"
              }
              {...register("question")}
            />
            {errors.question ? (
              <p className={styles.fieldError} id="liuyao-question-error" role="alert">
                {errors.question.message}
              </p>
            ) : null}
            <p className={styles.hint} id="liuyao-question-hint">
              只问一件事，尽量具体，不夹带多个问题。
            </p>
          </div>

          <div className={styles.field}>
            <label htmlFor="liuyao-event-datetime">起卦时刻</label>
            <input
              id="liuyao-event-datetime"
              type="datetime-local"
              step="1"
              autoComplete="off"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.event_datetime)}
              aria-describedby={
                errors.event_datetime ? "liuyao-event-datetime-error" : undefined
              }
              {...register("event_datetime")}
            />
            {errors.event_datetime ? (
              <p
                className={styles.fieldError}
                id="liuyao-event-datetime-error"
                role="alert"
              >
                {errors.event_datetime.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="liuyao-timezone">起卦时区</label>
            <select
              id="liuyao-timezone"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.timezone)}
              aria-describedby={errors.timezone ? "liuyao-timezone-error" : undefined}
              {...register("timezone")}
            >
              {TIMEZONES.map((timezone) => (
                <option key={timezone} value={timezone}>
                  {timezone}
                </option>
              ))}
            </select>
            {errors.timezone ? (
              <p className={styles.fieldError} id="liuyao-timezone-error" role="alert">
                {errors.timezone.message}
              </p>
            ) : null}
          </div>

          <div className={styles.field}>
            <label htmlFor="liuyao-location">起卦地点</label>
            <input
              id="liuyao-location"
              type="text"
              autoComplete="address-level2"
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.location)}
              aria-describedby={errors.location ? "liuyao-location-error" : undefined}
              {...register("location")}
            />
            {errors.location ? (
              <p className={styles.fieldError} id="liuyao-location-error" role="alert">
                {errors.location.message}
              </p>
            ) : null}
          </div>

          <fieldset className={styles.radioGroup}>
            <legend>起卦方式</legend>
            <div className={styles.radioOptions}>
              <label className={styles.radioOption}>
                <input
                  type="radio"
                  value="manual"
                  disabled={busy}
                  required
                  {...register("cast_mode")}
                />
                手动输入卦象
              </label>
              <label className={styles.radioOption}>
                <input
                  type="radio"
                  value="digital_coin"
                  disabled={busy}
                  required
                  {...register("cast_mode")}
                />
                电子摇卦
              </label>
            </div>
          </fieldset>

          {castMode === "manual" ? (
            <fieldset className={styles.tossGroup}>
              <legend>六次投掷（自下而上）</legend>
              <ol className={styles.tossGrid}>
                {tossKeys.map((key, index) => (
                  <li className={styles.field} key={key}>
                    <label htmlFor={`liuyao-toss-${index + 1}`}>
                      {tossNames[index]}
                    </label>
                    <select
                      id={`liuyao-toss-${index + 1}`}
                      disabled={busy}
                      required
                      aria-required="true"
                      aria-invalid={Boolean(errors[key])}
                      aria-describedby={
                        errors[key] ? `liuyao-toss-${index + 1}-error` : undefined
                      }
                      {...register(key)}
                    >
                      <option value="">请选择</option>
                      {[6, 7, 8, 9].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                    {errors[key] ? (
                      <p
                        className={styles.fieldError}
                        id={`liuyao-toss-${index + 1}-error`}
                        role="alert"
                      >
                        {errors[key]?.message}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
              <p className={styles.hint}>
                初爻在下方，上爻在上方；6 老阴，7 少阳，8 少阴，9 老阳。
              </p>
            </fieldset>
          ) : null}

          {submitError ? (
            <p className={styles.error} role="alert" aria-live="polite">
              {submitError}
            </p>
          ) : null}

          <button
            className={styles.submit}
            type="submit"
            disabled={busy}
            aria-busy={busy}
          >
            开始解读{busy ? " · 正在启动…" : ""}
          </button>
        </form>
      ) : null}
    </div>
  );
}
