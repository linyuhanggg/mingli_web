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
  startTimeCheckReading,
  type ProfileSummary,
  type TimeCheckStartRequest,
} from "@/lib/api";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";

import styles from "./fortune-flow.module.css";
import formControls from "./form-controls.module.css";

const CLOCK_TEXT = /^([01]\d|2[0-3]):[0-5]\d$/;
const DATE_TEXT = /^\d{4}-\d{2}-\d{2}$/;
const TIME_CHECK_EVENT_DOMAINS = [
  "career",
  "education",
  "finance",
  "relationship",
  "family",
  "location",
  "health",
] as const;
type TimeCheckEventDomain = (typeof TIME_CHECK_EVENT_DOMAINS)[number];

type TimeCheckEventFact = {
  event_id: string;
  occurred_at: string;
  domain: TimeCheckEventDomain;
};

function structuredEventLines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseStructuredEventLine(line: string): TimeCheckEventFact | null {
  const parts = line.split("|").map((part) => part.trim());
  if (parts.length !== 3) return null;
  const [occurredAt, domain, eventId] = parts;
  if (
    !DATE_TEXT.test(occurredAt) ||
    !TIME_CHECK_EVENT_DOMAINS.includes(domain as TimeCheckEventDomain) ||
    !eventId
  ) {
    return null;
  }
  return {
    occurred_at: occurredAt,
    domain: domain as TimeCheckEventDomain,
    event_id: eventId,
  };
}

const timeCheckSchema = z
  .object({
    profile_version_id: z.string().min(1, "请选择档案"),
    time_range_start: z.string().regex(CLOCK_TEXT, "请输入有效的开始时间"),
    time_range_end: z.string().regex(CLOCK_TEXT, "请输入有效的结束时间"),
    known_events: z.string().max(4000, "可核对事件不能超过 4000 个字符"),
    known_event_facts: z.string().max(2000, "结构化事件不能超过 2000 个字符"),
  })
  .superRefine((values, context) => {
    const eventCount = structuredEventLines(values.known_events).length;
    if (eventCount > 5) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["known_events"],
        message: "最多填写 5 条可核对事件，每行一条",
      });
    }
    const eventFactLines = structuredEventLines(values.known_event_facts);
    if (eventFactLines.length > 5) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["known_event_facts"],
        message: "最多填写 5 条结构化事件，每行一条",
      });
    }
    eventFactLines.forEach((line) => {
      if (parseStructuredEventLine(line)) return;
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["known_event_facts"],
        message: "结构化事件格式应为：YYYY-MM-DD | 领域 | 事件标识",
      });
    });
  });

type TimeCheckFormValues = z.infer<typeof timeCheckSchema>;

export function TimeCheckFlow() {
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
  } = useForm<TimeCheckFormValues>({
    resolver: zodResolver(timeCheckSchema),
    defaultValues: {
      profile_version_id: preselectedProfile ?? "",
      time_range_start: "00:00",
      time_range_end: "23:59",
      known_events: "",
      known_event_facts: "",
    },
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
      .catch((reason) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "档案加载失败，请稍后重试。");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadAttempt, preselectedProfile, setValue]);

  const handleStart = useCallback(
    async (values: TimeCheckFormValues) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setSubmitError("");
      const knownEvents = values.known_events
        ? structuredEventLines(values.known_events)
        : [];
      const knownEventFacts = structuredEventLines(values.known_event_facts)
        .map(parseStructuredEventLine)
        .filter((event): event is TimeCheckEventFact => event !== null);
      const payload: TimeCheckStartRequest = {
        profile_version_id: values.profile_version_id,
        time_range_start: values.time_range_start,
        time_range_end: values.time_range_end,
        known_events: knownEvents,
        ...(knownEventFacts.length > 0
          ? { known_event_facts: knownEventFacts }
          : {}),
        query: "围绕已确认出生档案生成十二个候选时辰事实",
        dimension_ids: ["time_options"],
      };
      const intent = stableKeyForIntent(intentKeyRef.current, payload);
      intentKeyRef.current = intent;
      try {
        const response = await startTimeCheckReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
      } catch (reason) {
        setSubmitError(
          reason instanceof Error ? reason.message : "寻时定盘任务启动失败，请稍后重试。",
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
      <h1>围绕未知时辰生成候选事实</h1>
      <p className={styles.lead}>
        选择已确认的出生档案，提交已知时间范围和可核对事件。服务端 Runtime 会用现有八字核心逐个生成十二个候选时辰；本页不在浏览器排盘。
      </p>
      <p className={styles.scopeNotice}>
        <strong>当前输出范围：十二候选、四柱原值、时间口径和有界候选证据排序。</strong>
        结构化事件只用于证据比较，不会直接生成“最可能时辰”的古法结论。
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
          <ButtonLink href="/app/profile/new">去建档</ButtonLink>
        </div>
      ) : null}

      {!loading && !error && profiles.length > 0 ? (
        <form
          className={styles.form}
          // eslint-disable-next-line react-hooks/refs -- react-hook-form invokes this only on submit
          onSubmit={handleSubmit(handleStart)}
          noValidate
          aria-busy={busy}
          aria-label="寻时定盘输入"
        >
          <div className={formControls.field}>
            <label htmlFor="time-check-profile">档案版本</label>
            <select
              id="time-check-profile"
              className={formControls.input}
              disabled={busy}
              required
              aria-required="true"
              aria-invalid={Boolean(errors.profile_version_id)}
              aria-describedby={
                errors.profile_version_id
                  ? "time-check-profile-error"
                  : "time-check-profile-help"
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
              <p className={formControls.error} id="time-check-profile-error" role="alert">
                {errors.profile_version_id.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="time-check-profile-help">
              只读取服务端确认的 ProfileVersion；出生资料不会被放进 URL，也不会由浏览器重新计算。
            </p>
          </div>

          <div className={styles.formGrid}>
            <div className={formControls.field}>
              <label htmlFor="time-check-range-start">已知时间范围·开始</label>
              <input
                id="time-check-range-start"
                className={formControls.input}
                type="time"
                step={60}
                disabled={busy}
                required
                aria-required="true"
                aria-invalid={Boolean(errors.time_range_start)}
                {...register("time_range_start")}
              />
              {errors.time_range_start ? (
                <p className={formControls.error} role="alert">
                  {errors.time_range_start.message}
                </p>
              ) : null}
            </div>
            <div className={formControls.field}>
              <label htmlFor="time-check-range-end">已知时间范围·结束</label>
              <input
                id="time-check-range-end"
                className={formControls.input}
                type="time"
                step={60}
                disabled={busy}
                required
                aria-required="true"
                aria-invalid={Boolean(errors.time_range_end)}
                {...register("time_range_end")}
              />
              {errors.time_range_end ? (
                <p className={formControls.error} role="alert">
                  {errors.time_range_end.message}
                </p>
              ) : null}
            </div>
          </div>
          <p className={formControls.hint}>
            可填写跨午夜范围，例如 22:00 到 02:00；Runtime 会保留完整十二候选并标记范围命中情况。
          </p>

          <div className={formControls.field}>
            <label htmlFor="time-check-events">可核对事件（可选，每行一条，最多 5 条）</label>
            <textarea
              id="time-check-events"
              className={formControls.input}
              rows={5}
              disabled={busy}
              aria-invalid={Boolean(errors.known_events)}
              aria-describedby="time-check-events-help"
              {...register("known_events")}
            />
            {errors.known_events ? (
              <p className={formControls.error} role="alert">
                {errors.known_events.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="time-check-events-help">
              这里只记录事件条数，当前不参与匹配、淘汰或排序；不要把它当成已完成的校验结果。
            </p>
          </div>

          <div className={formControls.field}>
            <label htmlFor="time-check-event-facts">
              结构化事件证据（可选，每行一条，最多 5 条）
            </label>
            <textarea
              id="time-check-event-facts"
              className={formControls.input}
              rows={5}
              disabled={busy}
              aria-invalid={Boolean(errors.known_event_facts)}
              aria-describedby="time-check-event-facts-help"
              placeholder="2018-07-01 | career | 开始工作"
              {...register("known_event_facts")}
            />
            {errors.known_event_facts ? (
              <p className={formControls.error} role="alert">
                {errors.known_event_facts.message}
              </p>
            ) : null}
            <p className={formControls.hint} id="time-check-event-facts-help">
              格式：YYYY-MM-DD | career/education/finance/relationship/family/location/health | 事件标识。只生成有界证据排序，不生成生命事件结论。
            </p>
          </div>

          {submitError ? <p className={styles.error} role="alert">{submitError}</p> : null}
          {busy ? (
            <p className={formControls.disabledReason} role="status">
              正在启动寻时定盘事实任务，选择与操作已暂时锁定。
            </p>
          ) : null}
          <div className={formControls.actions}>
            <button
              className={clsx(formControls.action, formControls.actionPrimary)}
              type="submit"
              disabled={busy}
              aria-busy={busy}
            >
              生成十二候选事实{busy ? " · 正在启动…" : ""}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
