"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { type FieldPath, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import styles from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";


const profileSchema = z
  .object({
    displayName: z.string().trim().max(20, "称呼最多 20 个字"),
    calendar: z.enum(["solar", "lunar"]),
    solarBirthDate: z.string(),
    lunarYear: z.string(),
    lunarMonth: z.string(),
    lunarDay: z.string(),
    birthTime: z.string(),
    unknownTime: z.boolean(),
    leapMonth: z.boolean(),
    birthPlace: z.string().trim().min(2, "请填写出生城市或地区").max(80, "地点最多 80 个字"),
    timezone: z.string().min(1, "请选择时区"),
    solarTime: z.boolean(),
    zi_hour_policy: z.enum(["", "midnight", "late-zi-next-day"]),
    sex: z.enum(["female", "male", "unspecified"]),
    consent: z.boolean().refine(Boolean, "请先确认资料用途与隐私说明"),
  })
  .superRefine((data, context) => {
    if (!data.zi_hour_policy) {
      context.addIssue({
        code: "custom",
        message: "请选择子时换日策略",
        path: ["zi_hour_policy"],
      });
    }
    if (data.calendar === "solar" && !data.solarBirthDate) {
      context.addIssue({ code: "custom", message: "请选择公历出生日期", path: ["solarBirthDate"] });
    }
    if (data.calendar === "lunar") {
      const lunarParts = [
        ["lunarYear", data.lunarYear, 1800, 2200, "请填写四位农历年"],
        ["lunarMonth", data.lunarMonth, 1, 12, "农历月应为 1 至 12"],
        ["lunarDay", data.lunarDay, 1, 30, "农历日应为 1 至 30"],
      ] as const;
      lunarParts.forEach(([path, value, minimum, maximum, message]) => {
        const number = Number(value);
        if (!/^\d+$/.test(value) || number < minimum || number > maximum) {
          context.addIssue({ code: "custom", message, path: [path] });
        }
      });
    }
    if (!data.unknownTime && !data.birthTime) {
      context.addIssue({
        code: "custom",
        message: "请选择出生时间，或勾选时辰不确定",
        path: ["birthTime"],
      });
    }
  });

type ProfileFormValues = z.infer<typeof profileSchema>;

const stepFields: Array<Array<FieldPath<ProfileFormValues>>> = [
  ["displayName", "sex"],
  [
    "calendar",
    "solarBirthDate",
    "lunarYear",
    "lunarMonth",
    "lunarDay",
    "birthTime",
    "unknownTime",
    "birthPlace",
    "timezone",
    "solarTime",
    "zi_hour_policy",
  ],
  ["consent"],
];

const steps = ["基本资料", "时间口径", "确认与同意"] as const;

function errorId(name: string) {
  return `profile-${name}-error`;
}

function formatBirthDate(values: Partial<ProfileFormValues>) {
  if (values.calendar === "lunar") {
    if (!values.lunarYear || !values.lunarMonth || !values.lunarDay) return "未填写";
    return `${values.lunarYear} 年 ${values.lunarMonth} 月 ${values.lunarDay} 日`;
  }
  return values.solarBirthDate || "未填写";
}

function formatZiHourPolicy(value: string | undefined) {
  if (value === "midnight") return "午夜换日（00:00） · midnight";
  if (value === "late-zi-next-day") return "晚子时换日（23:00 起算次日） · late-zi-next-day";
  return "未确认";
}

export function ProfileForm() {
  const [step, setStep] = useState(0);
  const [reviewed, setReviewed] = useState(false);
  const {
    register,
    handleSubmit,
    trigger,
    control,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      displayName: "",
      calendar: "solar",
      solarBirthDate: "",
      lunarYear: "",
      lunarMonth: "",
      lunarDay: "",
      birthTime: "",
      unknownTime: false,
      leapMonth: false,
      birthPlace: "",
      timezone: "Asia/Shanghai",
      solarTime: false,
      zi_hour_policy: "",
      sex: "unspecified",
      consent: false,
    },
    mode: "onBlur",
  });

  const values = useWatch({ control });
  const unknownTime = values.unknownTime;
  const calendar = values.calendar;

  async function goNext() {
    if (await trigger(stepFields[step], { shouldFocus: true })) {
      setStep((current) => Math.min(current + 1, steps.length - 1));
    }
  }

  function onSubmit() {
    setReviewed(true);
  }

  if (reviewed) {
    return (
      <div className={styles.formShell}>
        <StatusPanel
          state="success"
          title="资料已在本页核对"
          description="这只是前端核对结果，没有创建档案版本，也没有写入浏览器长期存储。正式保存与免费概览仍需登录及确定性 Runtime 接通。"
        />
        <dl className={styles.summary}>
          <div><dt>称呼</dt><dd>{values.displayName || "未填写"}</dd></div>
          <div><dt>出生口径</dt><dd>{values.calendar === "solar" ? "公历" : "农历"}</dd></div>
          <div><dt>出生日期</dt><dd>{formatBirthDate(values)}{values.calendar === "lunar" && values.leapMonth ? " · 闰月" : ""}</dd></div>
          <div><dt>出生时间</dt><dd>{values.unknownTime ? "时辰不确定" : values.birthTime}</dd></div>
          <div><dt>出生地 / 时区</dt><dd>{values.birthPlace} · {values.timezone}</dd></div>
          <div><dt>真太阳时</dt><dd>{values.solarTime ? "请求按真太阳时口径规范化" : "不使用"}</dd></div>
          <div><dt>zi_hour_policy</dt><dd>{formatZiHourPolicy(values.zi_hour_policy)}</dd></div>
        </dl>
        <button className={styles.button} type="button" disabled aria-describedby="profile-save-gate">
          保存并生成免费概览
        </button>
        <p className={styles.disabledReason} id="profile-save-gate">
          当前不可提交：确定性计算服务尚未接入，界面不会在浏览器里自行算盘。
        </p>
        <button className={styles.quietButton} type="button" onClick={() => setReviewed(false)}>
          返回修改资料
        </button>
      </div>
    );
  }

  return (
    <form className={styles.formShell} onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className={styles.formIntro}>
        <h2>{steps[step]}</h2>
        <p>只收本次排盘真正需要的资料。输入不会被写入 URL，也不会保存在 localStorage。</p>
      </div>

      <ol className={styles.stepList} aria-label="建档进度">
        {steps.map((label, index) => (
          <li key={label} data-active={index <= step} aria-current={index === step ? "step" : undefined}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{label}</strong>
          </li>
        ))}
      </ol>

      {step === 0 ? (
        <div className={styles.fieldGrid}>
          <div className={`${styles.field} ${styles.span2}`}>
            <label htmlFor="profile-name">姓名或称呼（可选）</label>
            <input
              className={styles.control}
              id="profile-name"
              autoComplete="name"
              aria-invalid={Boolean(errors.displayName)}
              aria-describedby={errors.displayName ? errorId("displayName") : "profile-name-help"}
              {...register("displayName")}
            />
            <p className={styles.help} id="profile-name-help">只用于你自己的档案辨认，不参与命理计算。</p>
            {errors.displayName ? <p className={styles.fieldError} id={errorId("displayName")} role="alert">{errors.displayName.message}</p> : null}
          </div>
          <fieldset className={`${styles.choiceGroup} ${styles.span2}`}>
            <legend className={styles.legend}>性别及必要术法口径 <span className={styles.required}>*</span></legend>
            {[
              ["female", "女"],
              ["male", "男"],
              ["unspecified", "暂不指定（部分能力可能无法继续）"],
            ].map(([value, label]) => (
              <label className={styles.choice} key={value}>
                <input type="radio" value={value} {...register("sex")} />
                <span>{label}</span>
              </label>
            ))}
          </fieldset>
        </div>
      ) : null}

      {step === 1 ? (
        <div className={styles.fieldGrid}>
          <fieldset className={`${styles.choiceGroup} ${styles.span2}`}>
            <legend className={styles.legend}>出生日期口径 <span className={styles.required}>*</span></legend>
            <label className={styles.choice}>
              <input type="radio" value="solar" {...register("calendar")} />
              <span><strong>公历</strong><small>按阳历日期输入</small></span>
            </label>
            <label className={styles.choice}>
              <input type="radio" value="lunar" {...register("calendar")} />
              <span><strong>农历</strong><small>后端会按确认的历法版本规范化</small></span>
            </label>
          </fieldset>
          {calendar === "solar" ? (
            <div className={`${styles.field} ${styles.span2}`}>
              <label htmlFor="profile-solar-date">公历出生日期 <span className={styles.required}>*</span></label>
              <input
                className={styles.control}
                id="profile-solar-date"
                type="date"
                autoComplete="bday"
                aria-invalid={Boolean(errors.solarBirthDate)}
                aria-describedby={errors.solarBirthDate ? errorId("solarBirthDate") : "profile-solar-date-help"}
                {...register("solarBirthDate")}
              />
              <p className={styles.help} id="profile-solar-date-help">这里只接受公历日期；切换农历后会改用独立的年、月、日字段。</p>
              {errors.solarBirthDate ? <p className={styles.fieldError} id={errorId("solarBirthDate")} role="alert">{errors.solarBirthDate.message}</p> : null}
            </div>
          ) : (
            <>
              <div className={`${styles.dateParts} ${styles.span2}`} aria-label="农历出生日期">
                <div className={styles.field}>
                  <label htmlFor="profile-lunar-year">农历年 <span className={styles.required}>*</span></label>
                  <input
                    className={styles.control}
                    id="profile-lunar-year"
                    type="text"
                    inputMode="numeric"
                    autoComplete="bday-year"
                    pattern="[0-9]*"
                    maxLength={4}
                    placeholder="例如 1990…"
                    aria-invalid={Boolean(errors.lunarYear)}
                    aria-describedby={errors.lunarYear ? errorId("lunarYear") : undefined}
                    {...register("lunarYear")}
                  />
                  {errors.lunarYear ? <p className={styles.fieldError} id={errorId("lunarYear")} role="alert">{errors.lunarYear.message}</p> : null}
                </div>
                <div className={styles.field}>
                  <label htmlFor="profile-lunar-month">农历月 <span className={styles.required}>*</span></label>
                  <input
                    className={styles.control}
                    id="profile-lunar-month"
                    type="text"
                    inputMode="numeric"
                    autoComplete="bday-month"
                    pattern="[0-9]*"
                    maxLength={2}
                    placeholder="1–12…"
                    aria-invalid={Boolean(errors.lunarMonth)}
                    aria-describedby={errors.lunarMonth ? errorId("lunarMonth") : undefined}
                    {...register("lunarMonth")}
                  />
                  {errors.lunarMonth ? <p className={styles.fieldError} id={errorId("lunarMonth")} role="alert">{errors.lunarMonth.message}</p> : null}
                </div>
                <div className={styles.field}>
                  <label htmlFor="profile-lunar-day">农历日 <span className={styles.required}>*</span></label>
                  <input
                    className={styles.control}
                    id="profile-lunar-day"
                    type="text"
                    inputMode="numeric"
                    autoComplete="bday-day"
                    pattern="[0-9]*"
                    maxLength={2}
                    placeholder="1–30…"
                    aria-invalid={Boolean(errors.lunarDay)}
                    aria-describedby={errors.lunarDay ? errorId("lunarDay") : undefined}
                    {...register("lunarDay")}
                  />
                  {errors.lunarDay ? <p className={styles.fieldError} id={errorId("lunarDay")} role="alert">{errors.lunarDay.message}</p> : null}
                </div>
              </div>
              <label className={`${styles.checkbox} ${styles.span2}`}>
                <input type="checkbox" {...register("leapMonth")} />
                <span>这是农历闰月（请只在原始资料明确写明“闰月”时勾选）</span>
              </label>
            </>
          )}
          <div className={styles.field}>
            <label htmlFor="profile-time">出生时间 <span className={styles.required}>*</span></label>
            <input
              className={styles.control}
              id="profile-time"
              type="time"
              autoComplete="off"
              disabled={unknownTime}
              aria-invalid={Boolean(errors.birthTime)}
              aria-describedby={errors.birthTime ? errorId("birthTime") : "profile-time-help"}
              {...register("birthTime")}
            />
            <p className={styles.help} id="profile-time-help">不确定时不要猜成子时，请使用下方选项。</p>
            {errors.birthTime ? <p className={styles.fieldError} id={errorId("birthTime")} role="alert">{errors.birthTime.message}</p> : null}
          </div>
          <label className={`${styles.checkbox} ${styles.span2}`}>
            <input type="checkbox" {...register("unknownTime")} />
            <span>出生时辰不确定；保留这个事实，不自动填成某个时辰</span>
          </label>
          <div className={styles.field}>
            <label htmlFor="profile-place">出生地 <span className={styles.required}>*</span></label>
            <input
              className={styles.control}
              id="profile-place"
              placeholder="例如：浙江省杭州市…"
              autoComplete="address-level2"
              aria-invalid={Boolean(errors.birthPlace)}
              aria-describedby={errors.birthPlace ? errorId("birthPlace") : "profile-place-help"}
              {...register("birthPlace")}
            />
            <p className={styles.help} id="profile-place-help">不自动索取精确定位；城市级信息用于确认时区与口径。</p>
            {errors.birthPlace ? <p className={styles.fieldError} id={errorId("birthPlace")} role="alert">{errors.birthPlace.message}</p> : null}
          </div>
          <div className={styles.field}>
            <label htmlFor="profile-timezone">时区 <span className={styles.required}>*</span></label>
            <select className={styles.control} id="profile-timezone" autoComplete="off" {...register("timezone")}>
              <option value="Asia/Shanghai">中国标准时间 · Asia/Shanghai</option>
              <option value="Asia/Hong_Kong">香港时间 · Asia/Hong_Kong</option>
              <option value="Asia/Taipei">台北时间 · Asia/Taipei</option>
              <option value="Asia/Singapore">新加坡时间 · Asia/Singapore</option>
            </select>
          </div>
          <label className={`${styles.checkbox} ${styles.span2}`}>
            <input type="checkbox" {...register("solarTime")} />
            <span>请求使用真太阳时口径；正式计算前会展示经度来源与校正结果供确认</span>
          </label>
          <fieldset
            className={`${styles.choiceGroup} ${styles.span2}`}
            aria-describedby={errors.zi_hour_policy ? errorId("zi_hour_policy") : "profile-zi-policy-help"}
          >
            <legend className={styles.legend}>子时换日策略（zi_hour_policy） <span className={styles.required}>*</span></legend>
            <label className={styles.choice}>
              <input type="radio" value="midnight" {...register("zi_hour_policy")} />
              <span><strong>午夜换日</strong><small>00:00 更换日柱 · Runtime 值 midnight</small></span>
            </label>
            <label className={styles.choice}>
              <input type="radio" value="late-zi-next-day" {...register("zi_hour_policy")} />
              <span><strong>晚子时换日</strong><small>23:00 起算次日日柱 · Runtime 值 late-zi-next-day</small></span>
            </label>
            <p className={styles.help} id="profile-zi-policy-help">两种策略可能改变 23:00–23:59 的日柱；即使时辰不确定，也必须保留明确口径。</p>
            {errors.zi_hour_policy ? <p className={styles.fieldError} id={errorId("zi_hour_policy")} role="alert">{errors.zi_hour_policy.message}</p> : null}
          </fieldset>
        </div>
      ) : null}

      {step === 2 ? (
        <div className={styles.fieldGrid}>
          <dl className={`${styles.summary} ${styles.span2}`}>
            <div><dt>称呼</dt><dd>{values.displayName || "未填写"}</dd></div>
            <div><dt>口径</dt><dd>{values.calendar === "solar" ? "公历" : `农历${values.leapMonth ? " · 闰月" : ""}`}</dd></div>
            <div><dt>日期 / 时间</dt><dd>{formatBirthDate(values)} · {values.unknownTime ? "时辰不确定" : values.birthTime || "未填写"}</dd></div>
            <div><dt>地点 / 时区</dt><dd>{values.birthPlace || "未填写"} · {values.timezone}</dd></div>
            <div><dt>真太阳时</dt><dd>{values.solarTime ? "请求使用，待服务端确认" : "不使用"}</dd></div>
            <div><dt>zi_hour_policy</dt><dd>{formatZiHourPolicy(values.zi_hour_policy)}</dd></div>
          </dl>
          <label className={`${styles.checkbox} ${styles.span2}`}>
            <input
              type="checkbox"
              aria-invalid={Boolean(errors.consent)}
              aria-describedby={errors.consent ? errorId("consent") : "profile-consent-help"}
              {...register("consent")}
            />
            <span>我确认以上资料用于本次命理试算，并已阅读开发期隐私说明。</span>
          </label>
          <p className={`${styles.help} ${styles.span2}`} id="profile-consent-help">
            游客草稿不承诺长期保存；登录后才会建立不可变档案版本。
          </p>
          {errors.consent ? <p className={`${styles.fieldError} ${styles.span2}`} id={errorId("consent")} role="alert">{errors.consent.message}</p> : null}
        </div>
      ) : null}

      <div className={styles.formActions}>
        {step > 0 ? (
          <button className={styles.secondaryButton} type="button" onClick={() => setStep((current) => current - 1)}>
            <ArrowLeft aria-hidden="true" size={18} />
            上一步
          </button>
        ) : null}
        {step < steps.length - 1 ? (
          <button className={styles.button} type="button" onClick={goNext}>
            继续确认
            <ArrowRight aria-hidden="true" size={18} />
          </button>
        ) : (
          <button className={styles.button} type="submit">
            <LockKeyhole aria-hidden="true" size={18} />
            完成本地核对
          </button>
        )}
      </div>
    </form>
  );
}
