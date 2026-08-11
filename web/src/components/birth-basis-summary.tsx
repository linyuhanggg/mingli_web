"use client";

import type { TimeBasisPolicy, ZiHourPolicy } from "@/lib/api";

import styles from "./birth-basis-summary.module.css";

export type BirthBasisSummaryValues = {
  birth_datetime: string;
  timezone: string;
  location: string;
  time_basis_policy: TimeBasisPolicy | "";
  zi_hour_policy: ZiHourPolicy | "";
  longitude?: string;
  latitude?: string;
};

const TIME_BASIS_LABELS: Record<TimeBasisPolicy, string> = {
  civil: "民用时",
  solar: "真太阳时",
  lunar: "农历时间口径",
};

const ZI_HOUR_LABELS: Record<ZiHourPolicy, string> = {
  midnight: "按午夜换日",
  substitute: "子时替代口径",
  solar: "按太阳时判断子时",
};

function Row({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className={styles.row}>
      <dt className={styles.rowLabel}>{label}</dt>
      <dd className={styles.rowValue}>{value}</dd>
    </div>
  );
}

/**
 * Live restatement of the confirmed birth basis, shown before profile submit.
 * It only mirrors what the user entered; the frontend never converts time or
 * calculates anything. The server remains the sole authority on time basis.
 */
export function BirthBasisSummary({
  values,
}: Readonly<{ values: BirthBasisSummaryValues }>) {
  const hasBirthTime = values.birth_datetime.trim().length > 0;
  const timeBasisLabel =
    values.time_basis_policy === ""
      ? "未选择"
      : TIME_BASIS_LABELS[values.time_basis_policy];
  const ziHourLabel =
    values.zi_hour_policy === ""
      ? "未选择"
      : ZI_HOUR_LABELS[values.zi_hour_policy];
  const longitude = values.longitude?.trim() ?? "";
  const isSolar = values.time_basis_policy === "solar";
  const isLunar = values.time_basis_policy === "lunar";

  return (
    <section className={styles.wrap} aria-label="提交前确认出生口径">
      <h3 className={styles.title}>提交前确认出生口径</h3>
      <dl className={styles.list}>
        <Row
          label="出生时间"
          value={hasBirthTime ? values.birth_datetime : "未填写"}
        />
        <Row label="出生时区" value={values.timezone.trim() || "未选择"} />
        <Row label="时间口径" value={timeBasisLabel} />
        <Row label="子时口径" value={ziHourLabel} />
        <Row label="出生地点" value={values.location.trim() || "未填写"} />
      </dl>

      {!hasBirthTime ? (
        <p className={styles.degraded}>
          未填写出生时间：时辰无法确认，后续排盘的确定性会降低。请按原始资料补全后再提交。
        </p>
      ) : null}

      {isSolar ? (
        <p className={styles.hint}>
          你选择的是真太阳时口径。前端只预览这一选择，不在本地做真太阳时换算；
          {longitude
            ? `已填写经度 ${longitude}°。`
            : "尚未填写经度，服务端可能退回民用时或要求补充地点信息。"}
        </p>
      ) : null}

      {isLunar ? (
        <p className={styles.hint}>
          你选择的是农历时间口径。请确认出生时间已按农历记录，服务端会按该口径规范化。
        </p>
      ) : null}

      <p className={styles.serverFinal}>最终以服务端口径为准。</p>
    </section>
  );
}
