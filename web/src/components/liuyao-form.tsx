"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LockKeyhole } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import styles from "./app-surface.module.css";
import { StatusPanel } from "./status-panel";


const castValue = z.enum(["", "6", "7", "8", "9"]);
const liuyaoSchema = z
  .object({
    question: z.string().trim().min(6, "请把问题写得更具体，至少 6 个字").max(120, "问题最多 120 个字"),
    timeScope: z.enum(["near", "three-months", "year", "custom"]),
    cast_mode: z.enum(["digital_coin", "manual"]),
    cast: z.tuple([castValue, castValue, castValue, castValue, castValue, castValue]),
    event_datetime: z.string().min(1, "请选择起卦或记录时刻"),
    confirmed_timezone: z.string().trim().min(1, "请确认 IANA 时区"),
    location: z.string().trim().min(2, "请填写起卦所在地（城市级）").max(80, "地点最多 80 个字"),
    consent: z.boolean().refine(Boolean, "请确认问题与卦象将作为同一个目标保存"),
  })
  .superRefine((data, context) => {
    if (data.confirmed_timezone && !/^[A-Za-z_]+(?:\/[A-Za-z0-9_+.-]+)+$/.test(data.confirmed_timezone)) {
      context.addIssue({
        code: "custom",
        message: "请输入 IANA 时区，例如 Asia/Shanghai",
        path: ["confirmed_timezone"],
      });
    }
    if (data.cast_mode !== "manual") return;
    data.cast.forEach((value, index) => {
      if (!value) {
        context.addIssue({ code: "custom", message: "请录入六爻", path: ["cast", index] });
      }
    });
  });

type LiuyaoFormValues = z.infer<typeof liuyaoSchema>;
const lineLabels = ["初爻（最下）", "二爻", "三爻", "四爻", "五爻", "上爻（最上）"] as const;
const castFields = ["cast.0", "cast.1", "cast.2", "cast.3", "cast.4", "cast.5"] as const;

export function LiuyaoForm() {
  const [reviewed, setReviewed] = useState(false);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<LiuyaoFormValues>({
    resolver: zodResolver(liuyaoSchema),
    defaultValues: {
      question: "",
      timeScope: "near",
      cast_mode: "digital_coin",
      cast: ["", "", "", "", "", ""],
      event_datetime: "",
      confirmed_timezone: "",
      location: "",
      consent: false,
    },
    mode: "onBlur",
  });
  const values = useWatch({ control });
  const castMode = values.cast_mode;
  const timeScope = values.timeScope ?? "near";
  const confirmedCast = castMode === "digital_coin"
    ? "digital_coin · 待 Runtime 安全起卦"
    : `[${(values.cast ?? []).map(Number).join(", ")}] · 自下而上`;

  if (reviewed) {
    return (
      <div className={styles.formShell}>
        <StatusPanel
          state="processing"
          title="问题与起卦方式已核对"
          description="这只是界面内的输入确认，没有生成卦象或解读。确定性起卦 Runtime 尚未接入，权益也没有被占用或核销。"
        />
        <dl className={styles.summary}>
          <div><dt>具体问题</dt><dd>{values.question}</dd></div>
          <div><dt>时间范围</dt><dd>{({ near: "近期", "three-months": "未来三个月", year: "一年内", custom: "自定义范围" } as const)[timeScope]}</dd></div>
          <div><dt>cast</dt><dd>{confirmedCast}</dd></div>
          <div><dt>event_datetime</dt><dd>{values.event_datetime}</dd></div>
          <div><dt>location / confirmed_timezone</dt><dd>{values.location} · {values.confirmed_timezone}</dd></div>
        </dl>
        <button className={styles.button} type="button" disabled aria-describedby="liuyao-runtime-gate">
          开始确定性起卦
        </button>
        <p className={styles.disabledReason} id="liuyao-runtime-gate">
          当前不可用：前端不会用随机占位数据冒充真实卦象。
        </p>
        <button className={styles.quietButton} type="button" onClick={() => setReviewed(false)}>
          返回修改问题
        </button>
      </div>
    );
  }

  return (
    <form className={styles.formShell} onSubmit={handleSubmit(() => setReviewed(true))} noValidate>
      <div className={styles.formIntro}>
        <h2>把一个问题说具体</h2>
        <p>一次解读只绑定一个问题、一个卦象与一个起卦时刻。换问题或换卦会形成新的购买目标。</p>
      </div>

      <div className={styles.fieldGrid}>
        <div className={`${styles.field} ${styles.span2}`}>
          <label htmlFor="liuyao-question">具体问题 <span className={styles.required}>*</span></label>
          <textarea
            className={styles.control}
            id="liuyao-question"
            autoComplete="off"
            placeholder="例如：我是否应该在三个月内接受已经拿到的这份工作邀请？…"
            aria-invalid={Boolean(errors.question)}
            aria-describedby={errors.question ? "liuyao-question-error" : "liuyao-question-help"}
            {...register("question")}
          />
          <p className={styles.help} id="liuyao-question-help">避免只写“事业如何”；写清事件、对象和希望判断的时间范围。</p>
          {errors.question ? <p className={styles.fieldError} id="liuyao-question-error" role="alert">{errors.question.message}</p> : null}
        </div>
        <div className={styles.field}>
          <label htmlFor="liuyao-scope">希望判断的时间范围 <span className={styles.required}>*</span></label>
          <select className={styles.control} id="liuyao-scope" autoComplete="off" {...register("timeScope")}>
            <option value="near">近期</option>
            <option value="three-months">未来三个月</option>
            <option value="year">一年内</option>
            <option value="custom">已在问题中写明</option>
          </select>
        </div>
        <div className={styles.field}>
          <label htmlFor="liuyao-time">起卦或记录时刻（event_datetime） <span className={styles.required}>*</span></label>
          <input
            className={styles.control}
            id="liuyao-time"
            type="datetime-local"
            autoComplete="off"
            aria-invalid={Boolean(errors.event_datetime)}
            aria-describedby={errors.event_datetime ? "liuyao-time-error" : "liuyao-time-help"}
            {...register("event_datetime")}
          />
          <p className={styles.help} id="liuyao-time-help">不自动回填设备时间；此处记录当地钟表时间，并与下方已确认时区配对。</p>
          {errors.event_datetime ? <p className={styles.fieldError} id="liuyao-time-error" role="alert">{errors.event_datetime.message}</p> : null}
        </div>
        <div className={styles.field}>
          <label htmlFor="liuyao-location">城市级地点（location） <span className={styles.required}>*</span></label>
          <input
            className={styles.control}
            id="liuyao-location"
            autoComplete="address-level2"
            placeholder="例如：上海市…"
            aria-invalid={Boolean(errors.location)}
            aria-describedby={errors.location ? "liuyao-location-error" : "liuyao-location-help"}
            {...register("location")}
          />
          <p className={styles.help} id="liuyao-location-help">城市级即可，不索取或伪造经纬度。</p>
          {errors.location ? <p className={styles.fieldError} id="liuyao-location-error" role="alert">{errors.location.message}</p> : null}
        </div>
        <div className={styles.field}>
          <label htmlFor="liuyao-timezone">已确认 IANA 时区（confirmed_timezone） <span className={styles.required}>*</span></label>
          <input
            className={styles.control}
            id="liuyao-timezone"
            type="text"
            inputMode="text"
            autoComplete="off"
            spellCheck="false"
            placeholder="例如：Asia/Shanghai…"
            aria-invalid={Boolean(errors.confirmed_timezone)}
            aria-describedby={errors.confirmed_timezone ? "liuyao-timezone-error" : "liuyao-timezone-help"}
            {...register("confirmed_timezone")}
          />
          <p className={styles.help} id="liuyao-timezone-help">不会读取或偷用浏览器时区；请按起卦地点主动确认 IANA 标识。</p>
          {errors.confirmed_timezone ? <p className={styles.fieldError} id="liuyao-timezone-error" role="alert">{errors.confirmed_timezone.message}</p> : null}
        </div>
      </div>

      <fieldset className={styles.choiceGroup}>
        <legend className={styles.legend}>cast 起卦值 <span className={styles.required}>*</span></legend>
        <label className={styles.choice}>
          <input type="radio" value="digital_coin" {...register("cast_mode")} />
          <span><strong>数字起卦 · digital_coin</strong><small>仅由 Runtime 的安全随机源生成并保存可重放事实；浏览器不生成随机数。</small></span>
        </label>
        <label className={styles.choice}>
          <input type="radio" value="manual" {...register("cast_mode")} />
          <span><strong>录入已有卦</strong><small>从初爻到上爻逐条录入，界面只记录，不自行解卦。</small></span>
        </label>
      </fieldset>

      {castMode === "manual" ? (
        <div className={styles.lineGrid} role="group" aria-label="六爻录入（自下而上）">
          {castFields.map((field, index) => (
            <div className={styles.field} key={field}>
              <label htmlFor={`liuyao-cast-${index}`}>{lineLabels[index]} <span className={styles.required}>*</span></label>
              <select
                className={styles.control}
                id={`liuyao-cast-${index}`}
                autoComplete="off"
                aria-invalid={Boolean(errors.cast?.[index])}
                aria-describedby={errors.cast?.[index] ? `liuyao-cast-${index}-error` : undefined}
                {...register(field)}
              >
                <option value="">请选择</option>
                <option value="6">6 · 老阴（变）</option>
                <option value="7">7 · 少阳</option>
                <option value="8">8 · 少阴</option>
                <option value="9">9 · 老阳（变）</option>
              </select>
              {errors.cast?.[index] ? <p className={styles.fieldError} id={`liuyao-cast-${index}-error`} role="alert">{errors.cast[index]?.message}</p> : null}
            </div>
          ))}
        </div>
      ) : null}

      <label className={styles.checkbox}>
        <input
          type="checkbox"
          aria-invalid={Boolean(errors.consent)}
          aria-describedby={errors.consent ? "liuyao-consent-error" : "liuyao-consent-help"}
          {...register("consent")}
        />
        <span>我确认问题、cast、event_datetime、城市与时区属于同一个目标；更换其中任一项需要重新起盘。</span>
      </label>
      <p className={styles.help} id="liuyao-consent-help">问题正文属于私密资料，不会进入 URL 或公共页面。</p>
      {errors.consent ? <p className={styles.fieldError} id="liuyao-consent-error" role="alert">{errors.consent.message}</p> : null}

      <div className={styles.formActions}>
        <button className={styles.button} type="submit">
          <LockKeyhole aria-hidden="true" size={18} />
          核对问题与方式
        </button>
      </div>
    </form>
  );
}
