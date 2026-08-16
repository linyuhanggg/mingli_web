"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, UsersRound } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState, type KeyboardEvent } from "react";
import { useForm, type FieldError, type UseFormRegister } from "react-hook-form";
import { z } from "zod";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";
import { ReadingResult } from "@/components/readings/reading-result";
import {
  confirmProfileDraft,
  createIdempotencyKey,
  createProfileDraft,
  startBaziRelationshipReading,
  startQizhengRelationshipReading,
  startZiweiRelationshipReading,
  type Gender,
  type ProfileConfirmRequest,
  type RelationshipStartRequest,
  type TimeBasisPolicy,
  type ZiHourPolicy,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { getProductDefinition, type ProductId } from "@/products/catalog";

import styles from "./relationship-task-page.module.css";

type RelationshipProductId = Extract<ProductId, "bazi" | "ziwei" | "qizheng">;

const relationshipModules: Record<RelationshipProductId, readonly string[]> = {
  bazi: ["甲方四柱与时间口径", "乙方四柱与时间口径", "十神互动、五行结构与关系主题"],
  ziwei: ["甲方十二宫与命宫摘要", "乙方十二宫与命宫摘要", "关系宫位、四化互动与时间层"],
  qizheng: ["甲方星盘与宿度", "乙方星盘与宿度", "关系宫位、星曜互动与限法边界"],
};

const relationshipSchema = z.object({
  aName: z.string().trim().min(1, "请填写甲方受测对象"),
  aDate: z.string().min(1, "请选择甲方出生日期"),
  aTime: z.string().min(1, "请选择甲方出生时间"),
  aLocation: z.string().trim().min(1, "请填写甲方出生地点"),
  aGender: z.enum(["", "female", "male", "other"]).refine((value) => value !== "", "请选择甲方性别"),
  aTimezone: z.string().trim().min(1, "请填写甲方时区"),
  aTimeBasis: z.enum(["", "civil", "solar"]).refine((value) => value !== "", "请选择甲方时间口径"),
  aZiHourPolicy: z.enum(["", "midnight", "substitute", "solar"]).refine((value) => value !== "", "请选择甲方子时口径"),
  aSubjectType: z.enum(["self", "other"]),
  aIsMinor: z.boolean(),
  aAuthorizationConfirmed: z.boolean(),
  aMinorGuardianConfirmed: z.boolean(),
  aLongitude: z.string().trim().refine((value) => value === "" || (Number.isFinite(Number(value)) && Number(value) >= -180 && Number(value) <= 180), "请输入甲方有效经度"),
  aLatitude: z.string().trim().refine((value) => value === "" || (Number.isFinite(Number(value)) && Number(value) >= -90 && Number(value) <= 90), "请输入甲方有效纬度"),
  aCoordinateSource: z.string().trim().max(40, "甲方坐标来源最多 40 个字"),
  bName: z.string().trim().min(1, "请填写乙方受测对象"),
  bDate: z.string().min(1, "请选择乙方出生日期"),
  bTime: z.string().min(1, "请选择乙方出生时间"),
  bLocation: z.string().trim().min(1, "请填写乙方出生地点"),
  bGender: z.enum(["", "female", "male", "other"]).refine((value) => value !== "", "请选择乙方性别"),
  bTimezone: z.string().trim().min(1, "请填写乙方时区"),
  bTimeBasis: z.enum(["", "civil", "solar"]).refine((value) => value !== "", "请选择乙方时间口径"),
  bZiHourPolicy: z.enum(["", "midnight", "substitute", "solar"]).refine((value) => value !== "", "请选择乙方子时口径"),
  bSubjectType: z.enum(["self", "other"]),
  bIsMinor: z.boolean(),
  bAuthorizationConfirmed: z.boolean(),
  bMinorGuardianConfirmed: z.boolean(),
  bLongitude: z.string().trim().refine((value) => value === "" || (Number.isFinite(Number(value)) && Number(value) >= -180 && Number(value) <= 180), "请输入乙方有效经度"),
  bLatitude: z.string().trim().refine((value) => value === "" || (Number.isFinite(Number(value)) && Number(value) >= -90 && Number(value) <= 90), "请输入乙方有效纬度"),
  bCoordinateSource: z.string().trim().max(40, "乙方坐标来源最多 40 个字"),
  relationship: z.enum(["couple", "spouse", "parent-child", "partner", "work", "friend"]),
});

function relationshipSchemaFor(productId: RelationshipProductId) {
  return relationshipSchema.superRefine((data, context) => {
    for (const side of ["a", "b"] as const) {
      const basis = data[`${side}TimeBasis`];
      const coordinateRequired = productId === "qizheng" || basis === "solar";
      if (!coordinateRequired) continue;
      for (const field of ["Longitude", "Latitude", "CoordinateSource"] as const) {
        const key = `${side}${field}` as keyof RelationshipFormValues;
        const value = data[key];
        if (typeof value !== "string" || !value.trim()) {
          context.addIssue({
            code: "custom",
            path: [key],
            message: `${side === "a" ? "甲方" : "乙方"}采用该时间口径时必须确认坐标与来源`,
          });
        }
      }
    }
    for (const side of ["a", "b"] as const) {
      const label = side === "a" ? "甲方" : "乙方";
      if (data[`${side}SubjectType`] === "other" && !data[`${side}AuthorizationConfirmed`]) {
        context.addIssue({
          code: "custom",
          path: [`${side}AuthorizationConfirmed`],
          message: `${label}是他人资料时必须确认已获得本人授权`,
        });
      }
      if (data[`${side}IsMinor`] && !data[`${side}MinorGuardianConfirmed`]) {
        context.addIssue({
          code: "custom",
          path: [`${side}MinorGuardianConfirmed`],
          message: `${label}是未成年人时必须确认已获得监护人确认`,
        });
      }
    }
  });
}

type RelationshipFormValues = z.input<typeof relationshipSchema>;

const relationshipDefaults: RelationshipFormValues = {
  aName: "",
  aDate: "",
  aTime: "",
  aLocation: "",
  aGender: "",
  aTimezone: "Asia/Shanghai",
  aTimeBasis: "",
  aZiHourPolicy: "midnight",
  aSubjectType: "self",
  aIsMinor: false,
  aAuthorizationConfirmed: false,
  aMinorGuardianConfirmed: false,
  aLongitude: "",
  aLatitude: "",
  aCoordinateSource: "",
  bName: "",
  bDate: "",
  bTime: "",
  bLocation: "",
  bGender: "",
  bTimezone: "Asia/Shanghai",
  bTimeBasis: "",
  bZiHourPolicy: "midnight",
  bSubjectType: "self",
  bIsMinor: false,
  bAuthorizationConfirmed: false,
  bMinorGuardianConfirmed: false,
  bLongitude: "",
  bLatitude: "",
  bCoordinateSource: "",
  relationship: "couple",
};

const relationshipErrorFields: Record<keyof RelationshipFormValues, { id: string; label: string }> = {
  aName: { id: "a-name", label: "甲方受测对象" },
  aDate: { id: "a-date", label: "甲方出生日期" },
  aTime: { id: "a-time", label: "甲方出生时间" },
  aLocation: { id: "a-location", label: "甲方出生地点" },
  aGender: { id: "a-gender", label: "甲方性别" },
  aTimezone: { id: "a-timezone", label: "甲方出生时区" },
  aTimeBasis: { id: "a-time-basis", label: "甲方时间口径" },
  aZiHourPolicy: { id: "a-zi-hour-policy", label: "甲方子时口径" },
  aSubjectType: { id: "a-subject-type", label: "甲方资料主体" },
  aIsMinor: { id: "a-is-minor", label: "甲方未成年人标记" },
  aAuthorizationConfirmed: { id: "a-authorization-confirmed", label: "甲方授权确认" },
  aMinorGuardianConfirmed: { id: "a-minor-guardian-confirmed", label: "甲方监护人确认" },
  bName: { id: "b-name", label: "乙方受测对象" },
  bDate: { id: "b-date", label: "乙方出生日期" },
  bTime: { id: "b-time", label: "乙方出生时间" },
  bLocation: { id: "b-location", label: "乙方出生地点" },
  bGender: { id: "b-gender", label: "乙方性别" },
  bTimezone: { id: "b-timezone", label: "乙方出生时区" },
  bTimeBasis: { id: "b-time-basis", label: "乙方时间口径" },
  bZiHourPolicy: { id: "b-zi-hour-policy", label: "乙方子时口径" },
  bSubjectType: { id: "b-subject-type", label: "乙方资料主体" },
  bIsMinor: { id: "b-is-minor", label: "乙方未成年人标记" },
  bAuthorizationConfirmed: { id: "b-authorization-confirmed", label: "乙方授权确认" },
  bMinorGuardianConfirmed: { id: "b-minor-guardian-confirmed", label: "乙方监护人确认" },
  aLongitude: { id: "a-longitude", label: "甲方出生经度" },
  aLatitude: { id: "a-latitude", label: "甲方出生纬度" },
  aCoordinateSource: { id: "a-coordinate-source", label: "甲方坐标来源" },
  bLongitude: { id: "b-longitude", label: "乙方出生经度" },
  bLatitude: { id: "b-latitude", label: "乙方出生纬度" },
  bCoordinateSource: { id: "b-coordinate-source", label: "乙方坐标来源" },
  relationship: { id: "relationship", label: "关系类型" },
};

const relationshipTypeByFormValue: Record<
  RelationshipFormValues["relationship"],
  RelationshipStartRequest["relationship_type"]
> = {
  couple: "romantic",
  spouse: "married",
  "parent-child": "parent_child",
  partner: "business",
  work: "work",
  friend: "friend",
};

function optionalCoordinate(value: string): number | undefined {
  const normalized = value.trim();
  return normalized === "" ? undefined : Number(normalized);
}

function profileBody(
  values: RelationshipFormValues,
  side: "a" | "b",
): ProfileConfirmRequest {
  const get = (suffix: string) =>
    values[`${side}${suffix}` as keyof RelationshipFormValues] as string;
  const getFlag = (suffix: string) =>
    Boolean(values[`${side}${suffix}` as keyof RelationshipFormValues]);
  return {
    birth_datetime: localDateTimeWithOffset(
      `${get("Date")}T${get("Time")}`,
      get("Timezone"),
    ),
    timezone: get("Timezone"),
    location: get("Location").trim(),
    gender: get("Gender") as Gender,
    time_basis_policy: get("TimeBasis") as TimeBasisPolicy,
    zi_hour_policy: get("ZiHourPolicy") as ZiHourPolicy,
    longitude: optionalCoordinate(get("Longitude")),
    latitude: optionalCoordinate(get("Latitude")),
    coordinate_source: get("CoordinateSource").trim() || undefined,
    subject_type: get("SubjectType") as "self" | "other",
    is_minor: getFlag("IsMinor"),
    authorization_confirmed: getFlag("AuthorizationConfirmed"),
    minor_guardian_confirmed: getFlag("MinorGuardianConfirmed"),
  };
}

type PersonErrorField =
  | "name"
  | "date"
  | "time"
  | "location"
  | "gender"
  | "timezone"
  | "timeBasis"
  | "ziHourPolicy"
  | "subjectType"
  | "authorizationConfirmed"
  | "minorGuardianConfirmed"
  | "longitude"
  | "latitude"
  | "coordinateSource";

function PersonFields({
  errors,
  productId,
  productName,
  register,
  side,
}: {
  errors: Partial<Record<PersonErrorField, FieldError>>;
  productId: RelationshipProductId;
  productName: string;
  register: UseFormRegister<RelationshipFormValues>;
  side: "甲方" | "乙方";
}) {
  const prefix = side === "甲方" ? "a" : "b";
  const fields = prefix === "a"
    ? {
        name: "aName", date: "aDate", time: "aTime", location: "aLocation",
        gender: "aGender", timezone: "aTimezone", timeBasis: "aTimeBasis",
        ziHourPolicy: "aZiHourPolicy", longitude: "aLongitude", latitude: "aLatitude",
        coordinateSource: "aCoordinateSource", subjectType: "aSubjectType",
        isMinor: "aIsMinor", authorizationConfirmed: "aAuthorizationConfirmed",
        minorGuardianConfirmed: "aMinorGuardianConfirmed",
      } as const
    : {
        name: "bName", date: "bDate", time: "bTime", location: "bLocation",
        gender: "bGender", timezone: "bTimezone", timeBasis: "bTimeBasis",
        ziHourPolicy: "bZiHourPolicy", longitude: "bLongitude", latitude: "bLatitude",
        coordinateSource: "bCoordinateSource", subjectType: "bSubjectType",
        isMinor: "bIsMinor", authorizationConfirmed: "bAuthorizationConfirmed",
        minorGuardianConfirmed: "bMinorGuardianConfirmed",
      } as const;
  const fieldId = (name: string) => `${productId}-${prefix}-${name}`;

  return (
    <fieldset className={styles.person}>
      <legend>{side}资料</legend>
      <label htmlFor={fieldId("name")}>受测对象</label>
      <input
        aria-describedby={errors.name ? `${fieldId("name")}-error` : undefined}
        aria-invalid={Boolean(errors.name)}
        aria-label={`${side}受测对象`}
        autoComplete="off"
        id={fieldId("name")}
        placeholder={`${side}称呼`}
        required
        {...register(fields.name)}
      />
      {errors.name ? <p className={styles.fieldError} id={`${fieldId("name")}-error`} role="alert">{errors.name.message}</p> : null}
      <label htmlFor={fieldId("gender")}>性别</label>
      <select
        aria-describedby={errors.gender ? `${fieldId("gender")}-error` : undefined}
        aria-invalid={Boolean(errors.gender)}
        aria-label={`${side}性别`}
        id={fieldId("gender")}
        {...register(fields.gender)}
      >
        <option value="">请选择</option>
        <option value="female">女</option>
        <option value="male">男</option>
        <option value="other">其他</option>
      </select>
      {errors.gender ? <p className={styles.fieldError} id={`${fieldId("gender")}-error`} role="alert">{errors.gender.message}</p> : null}
      <div className={styles.twoColumns}>
        <div>
          <label htmlFor={fieldId("date")}>出生日期</label>
          <input
            aria-describedby={errors.date ? `${fieldId("date")}-error` : undefined}
            aria-invalid={Boolean(errors.date)}
            aria-label={`${side}出生日期`}
            autoComplete="off"
            id={fieldId("date")}
            required
            type="date"
            {...register(fields.date)}
          />
          {errors.date ? <p className={styles.fieldError} id={`${fieldId("date")}-error`} role="alert">{errors.date.message}</p> : null}
        </div>
        <div>
          <label htmlFor={fieldId("time")}>出生时间</label>
          <input
            aria-describedby={errors.time ? `${fieldId("time")}-error` : undefined}
            aria-invalid={Boolean(errors.time)}
            aria-label={`${side}出生时间`}
            autoComplete="off"
            id={fieldId("time")}
            required
            type="time"
            {...register(fields.time)}
          />
          {errors.time ? <p className={styles.fieldError} id={`${fieldId("time")}-error`} role="alert">{errors.time.message}</p> : null}
        </div>
      </div>
      <label htmlFor={fieldId("location")}>出生地点</label>
      <input
        aria-describedby={errors.location ? `${fieldId("location")}-error` : undefined}
        aria-invalid={Boolean(errors.location)}
        aria-label={`${side}出生地点`}
        autoComplete="off"
        id={fieldId("location")}
        placeholder="省 / 市 / 区县"
        required
        {...register(fields.location)}
      />
      {errors.location ? <p className={styles.fieldError} id={`${fieldId("location")}-error`} role="alert">{errors.location.message}</p> : null}
      <label htmlFor={fieldId("timezone")}>出生时区</label>
      <input
        aria-describedby={errors.timezone ? `${fieldId("timezone")}-error` : undefined}
        aria-invalid={Boolean(errors.timezone)}
        aria-label={`${side}出生时区`}
        autoComplete="off"
        id={fieldId("timezone")}
        placeholder="Asia/Shanghai"
        required
        {...register(fields.timezone)}
      />
      {errors.timezone ? <p className={styles.fieldError} id={`${fieldId("timezone")}-error`} role="alert">{errors.timezone.message}</p> : null}
      <div className={styles.twoColumns}>
        <div>
          <label htmlFor={fieldId("time-basis")}>时间口径</label>
          <select
            aria-describedby={errors.timeBasis ? `${fieldId("time-basis")}-error` : undefined}
            aria-invalid={Boolean(errors.timeBasis)}
            aria-label={`${side}时间口径`}
            id={fieldId("time-basis")}
            {...register(fields.timeBasis)}
          >
            <option value="">请选择</option>
            <option value="civil">民用时</option>
            <option value="solar">真太阳时</option>
          </select>
          {errors.timeBasis ? <p className={styles.fieldError} id={`${fieldId("time-basis")}-error`} role="alert">{errors.timeBasis.message}</p> : null}
        </div>
        <div>
          <label htmlFor={fieldId("zi-hour-policy")}>子时口径</label>
          <select
            aria-describedby={errors.ziHourPolicy ? `${fieldId("zi-hour-policy")}-error` : undefined}
            aria-invalid={Boolean(errors.ziHourPolicy)}
            aria-label={`${side}子时口径`}
            id={fieldId("zi-hour-policy")}
            {...register(fields.ziHourPolicy)}
          >
            <option value="midnight">按午夜换日</option>
            <option value="substitute">子时替代口径</option>
            <option value="solar">按太阳时判断子时</option>
          </select>
          {errors.ziHourPolicy ? <p className={styles.fieldError} id={`${fieldId("zi-hour-policy")}-error`} role="alert">{errors.ziHourPolicy.message}</p> : null}
        </div>
      </div>
      <div className={styles.twoColumns}>
        <div>
          <label htmlFor={fieldId("longitude")}>出生经度{productId === "qizheng" ? "（必填）" : ""}</label>
          <input
            aria-describedby={errors.longitude ? `${fieldId("longitude")}-error` : undefined}
            aria-invalid={Boolean(errors.longitude)}
            aria-label={`${side}出生经度`}
            id={fieldId("longitude")}
            inputMode="decimal"
            placeholder="东经为正"
            {...register(fields.longitude)}
          />
          {errors.longitude ? <p className={styles.fieldError} id={`${fieldId("longitude")}-error`} role="alert">{errors.longitude.message}</p> : null}
        </div>
        <div>
          <label htmlFor={fieldId("latitude")}>出生纬度{productId === "qizheng" ? "（必填）" : ""}</label>
          <input
            aria-describedby={errors.latitude ? `${fieldId("latitude")}-error` : undefined}
            aria-invalid={Boolean(errors.latitude)}
            aria-label={`${side}出生纬度`}
            id={fieldId("latitude")}
            inputMode="decimal"
            placeholder="北纬为正"
            {...register(fields.latitude)}
          />
          {errors.latitude ? <p className={styles.fieldError} id={`${fieldId("latitude")}-error`} role="alert">{errors.latitude.message}</p> : null}
        </div>
      </div>
      <label htmlFor={fieldId("coordinate-source")}>坐标来源{productId === "qizheng" ? "（必填）" : ""}</label>
      <input
        aria-describedby={errors.coordinateSource ? `${fieldId("coordinate-source")}-error` : undefined}
        aria-invalid={Boolean(errors.coordinateSource)}
        aria-label={`${side}坐标来源`}
        id={fieldId("coordinate-source")}
        placeholder="例如用户确认或城市地理编码"
        {...register(fields.coordinateSource)}
      />
      {errors.coordinateSource ? <p className={styles.fieldError} id={`${fieldId("coordinate-source")}-error`} role="alert">{errors.coordinateSource.message}</p> : null}
      <label htmlFor={fieldId("subject-type")}>资料主体</label>
      <select
        aria-describedby={errors.subjectType ? `${fieldId("subject-type")}-error` : undefined}
        aria-invalid={Boolean(errors.subjectType)}
        aria-label={`${side}资料主体`}
        id={fieldId("subject-type")}
        {...register(fields.subjectType)}
      >
        <option value="self">本人资料</option>
        <option value="other">他人资料</option>
      </select>
      {errors.subjectType ? <p className={styles.fieldError} id={`${fieldId("subject-type")}-error`} role="alert">{errors.subjectType.message}</p> : null}
      <label className={styles.checkRow}>
        <input type="checkbox" {...register(fields.isMinor)} />
        <span>这是未成年人资料</span>
      </label>
      <label className={styles.checkRow}>
        <input
          aria-describedby={errors.authorizationConfirmed ? `${fieldId("authorization-confirmed")}-error` : undefined}
          aria-invalid={Boolean(errors.authorizationConfirmed)}
          id={fieldId("authorization-confirmed")}
          type="checkbox"
          {...register(fields.authorizationConfirmed)}
        />
        <span>如为他人资料，我已获得本人授权</span>
      </label>
      {errors.authorizationConfirmed ? <p className={styles.fieldError} id={`${fieldId("authorization-confirmed")}-error`} role="alert">{errors.authorizationConfirmed.message}</p> : null}
      <label className={styles.checkRow}>
        <input
          aria-describedby={errors.minorGuardianConfirmed ? `${fieldId("minor-guardian-confirmed")}-error` : undefined}
          aria-invalid={Boolean(errors.minorGuardianConfirmed)}
          id={fieldId("minor-guardian-confirmed")}
          type="checkbox"
          {...register(fields.minorGuardianConfirmed)}
        />
        <span>如为未成年人资料，我已获得监护人确认</span>
      </label>
      {errors.minorGuardianConfirmed ? <p className={styles.fieldError} id={`${fieldId("minor-guardian-confirmed")}-error`} role="alert">{errors.minorGuardianConfirmed.message}</p> : null}
      <p>{productName}会分别绑定双方资料版本；更改任一方会创建新任务。</p>
    </fieldset>
  );
}

export function RelationshipTaskPage({ productId }: { productId: RelationshipProductId }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const readingId = searchParams.get("reading");
  const product = getProductDefinition(productId);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [activeRegion, setActiveRegion] = useState<0 | 1 | 2>(0);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const {
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<RelationshipFormValues>({
    defaultValues: relationshipDefaults,
    mode: "onSubmit",
    resolver: zodResolver(relationshipSchemaFor(productId)),
    shouldFocusError: true,
  });
  const validationErrors = (Object.keys(errors) as Array<keyof RelationshipFormValues>)
    .map((fieldName) => relationshipErrorFields[fieldName]);

  const handleCheck = () => {
    setSubmitError(null);
    setChecked(true);
  };

  const handleCreateReading = async (values: RelationshipFormValues) => {
    if (busy) return;
    setBusy(true);
    setSubmitError(null);
    try {
      const [firstDraft, secondDraft] = await Promise.all([
        createProfileDraft(values.aName.trim()),
        createProfileDraft(values.bName.trim()),
      ]);
      const [first, second] = await Promise.all([
        confirmProfileDraft(firstDraft.draft_id, profileBody(values, "a")),
        confirmProfileDraft(secondDraft.draft_id, profileBody(values, "b")),
      ]);
      const payload: RelationshipStartRequest = {
        profile_version_ids: [first.profile_version_id, second.profile_version_id],
        relationship_type: relationshipTypeByFormValue[values.relationship],
        dimension_ids: ["relationship"],
      };
      const idempotencyKey = createIdempotencyKey();
      const response =
        productId === "bazi"
          ? await startBaziRelationshipReading(payload, idempotencyKey)
          : productId === "ziwei"
            ? await startZiweiRelationshipReading(payload, idempotencyKey)
            : await startQizhengRelationshipReading(payload, idempotencyKey);
      router.push(`/${productId}/hepan?reading=${encodeURIComponent(response.reading_version_id)}`);
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : "合盘任务创建失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  };

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % 3;
    if (event.key === "ArrowLeft") nextIndex = (index + 2) % 3;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = 2;
    if (nextIndex === null) return;
    event.preventDefault();
    setActiveRegion(nextIndex as 0 | 1 | 2);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          {readingId ? (
            <>
              <header className={styles.hero}>
                <a href={`/${productId}/hepan`}><ArrowLeft aria-hidden="true" size={16} /> 返回合盘输入</a>
                <div><UsersRound aria-hidden="true" size={27} strokeWidth={1.6} /><h1>{product.name}双人合盘结果</h1></div>
                <p>当前产品路由内展示服务端生成的双方结构事实。</p>
              </header>
              <ReadingResult readingId={readingId} />
            </>
          ) : null}
          {readingId ? null : (
          <>
          <header className={styles.hero}>
            <a href={product.href}><ArrowLeft aria-hidden="true" size={16} /> 返回{product.name}</a>
            <div><UsersRound aria-hidden="true" size={27} strokeWidth={1.6} /><h1>{product.name}双人合盘</h1></div>
            <p>甲乙双方盘面与关系区分开呈现，不把合盘塞进单盘小卡，也不混入命盘合参。</p>
          </header>

          <form
            aria-label={`${product.name}双人合盘输入`}
            className={styles.form}
            noValidate
            onSubmit={handleSubmit(
              handleCheck,
              () => setChecked(false),
            )}
          >
            {validationErrors.length > 0 ? (
              <div
                aria-labelledby={`${product.id}-relationship-error-summary-title`}
                className={styles.errorSummary}
                role="alert"
              >
                <h2 id={`${product.id}-relationship-error-summary-title`}>请先修正双方资料</h2>
                <ul>
                  {validationErrors.map((field) => (
                    <li key={field.id}><a href={`#${product.id}-${field.id}`}>{field.label}</a></li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className={styles.peopleGrid}>
              <PersonFields
                errors={{
                  name: errors.aName,
                  date: errors.aDate,
                  time: errors.aTime,
                  location: errors.aLocation,
                  gender: errors.aGender,
                  timezone: errors.aTimezone,
                  timeBasis: errors.aTimeBasis,
                  ziHourPolicy: errors.aZiHourPolicy,
                  subjectType: errors.aSubjectType,
                  authorizationConfirmed: errors.aAuthorizationConfirmed,
                  minorGuardianConfirmed: errors.aMinorGuardianConfirmed,
                  longitude: errors.aLongitude,
                  latitude: errors.aLatitude,
                  coordinateSource: errors.aCoordinateSource,
                }}
                productId={productId}
                productName={product.name}
                register={register}
                side="甲方"
              />
              <PersonFields
                errors={{
                  name: errors.bName,
                  date: errors.bDate,
                  time: errors.bTime,
                  location: errors.bLocation,
                  gender: errors.bGender,
                  timezone: errors.bTimezone,
                  timeBasis: errors.bTimeBasis,
                  ziHourPolicy: errors.bZiHourPolicy,
                  subjectType: errors.bSubjectType,
                  authorizationConfirmed: errors.bAuthorizationConfirmed,
                  minorGuardianConfirmed: errors.bMinorGuardianConfirmed,
                  longitude: errors.bLongitude,
                  latitude: errors.bLatitude,
                  coordinateSource: errors.bCoordinateSource,
                }}
                productId={productId}
                productName={product.name}
                register={register}
                side="乙方"
              />
            </div>
            <div className={styles.relationshipField}>
              <label htmlFor={`${product.id}-relationship`}>关系类型</label>
              <select autoComplete="off" id={`${product.id}-relationship`} {...register("relationship")}>
                <option value="couple">情侣</option>
                <option value="spouse">夫妻</option>
                <option value="parent-child">亲子</option>
                <option value="partner">合伙</option>
                <option value="work">职场</option>
                <option value="friend">朋友</option>
              </select>
              <p>关系类型会绑定到本次任务，变更后创建新任务。</p>
            </div>
            <button className={styles.primaryButton} type="submit">检查双方资料</button>
            {checked ? (
              <>
                <p className={styles.checked} role="status"><Check aria-hidden="true" size={17} /> 输入结构已检查；双方资料会分别保存为不可变 ProfileVersion。</p>
                {submitError ? <p className={styles.formError} role="alert">{submitError}</p> : null}
                <button
                  className={styles.primaryButton}
                  disabled={busy}
                  onClick={() => void handleSubmit(handleCreateReading)()}
                  type="button"
                >
                  {busy ? "正在创建双方档案并生成合盘…" : "创建档案并生成合盘"}
                </button>
              </>
            ) : null}
          </form>

          <section className={styles.workspace} aria-labelledby={`${product.id}-relationship-workspace`}>
            <div className={styles.workspaceHeading}>
              <div><h2 id={`${product.id}-relationship-workspace`}>甲方 / 乙方 / 关系区</h2><p>桌面三段并列；平板和手机可按区切换。</p></div>
              <span>无结果数据</span>
            </div>
            <div className={styles.tabs} role="tablist" aria-label="合盘区域">
              {(["甲方", "乙方", "关系"] as const).map((label, index) => (
                <button
                  aria-controls={`${product.id}-relationship-region-${index}`}
                  aria-selected={activeRegion === index}
                  id={`${product.id}-relationship-tab-${index}`}
                  key={label}
                  onClick={() => setActiveRegion(index as 0 | 1 | 2)}
                  onKeyDown={(event) => handleTabKeyDown(event, index)}
                  ref={(node) => { tabRefs.current[index] = node; }}
                  role="tab"
                  tabIndex={activeRegion === index ? 0 : -1}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
            <div className={styles.moduleGrid}>
              {relationshipModules[productId].map((module, index) => (
                <article
                  aria-labelledby={`${product.id}-relationship-tab-${index}`}
                  data-active={activeRegion === index}
                  id={`${product.id}-relationship-region-${index}`}
                  key={module}
                  role="tabpanel"
                >
                  <span>{index === 0 ? "甲方" : index === 1 ? "乙方" : "关系"}</span><h3>{module}</h3><p>等待双方真实 {product.name} ViewModel。</p>
                </article>
              ))}
            </div>
            <Status state="processing" title={`${product.name}双人任务接线已完成`} description="确认后由 Runtime 分别计算双方命盘；只有 Runtime 原生关系事实存在时才展示跨盘信号，页面不在浏览器计算。" />
          </section>
          </>
          )}
        </Container>
      </main>
    </PublicPageShell>
  );
}
