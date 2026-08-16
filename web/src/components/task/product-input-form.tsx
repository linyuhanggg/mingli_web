"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Camera, Info, Upload } from "lucide-react";
import { useMemo, useRef, useState, type ChangeEvent } from "react";
import { useForm, useWatch, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { z } from "zod";

import { Status } from "@/components/ui/status";
import { IanaTimeZoneOptions } from "@/components/iana-timezone-options";
import { isIanaTimeZone } from "@/lib/iana-timezones";
import type { ProductDefinition } from "@/products/catalog";

import styles from "./task-shell.module.css";

const taskSchemaBase = z.object({
  subject: z.string(),
  calendar: z.string(),
  birthDate: z.string(),
  birthTime: z.string(),
  targetYear: z.string(),
  targetMonth: z.string(),
  targetDate: z.string(),
  unknownTime: z.boolean(),
  location: z.string(),
  timezone: z.string(),
  gender: z.string(),
  timeStandard: z.string(),
  longitude: z.string(),
  latitude: z.string(),
  coordinateSource: z.string(),
  issue: z.string(),
  focus: z.string(),
  eventTime: z.string(),
  divinationMethod: z.string(),
  meihuaCastingMethod: z.string(),
  meihuaNumber: z.string(),
  meihuaCount: z.string(),
  meihuaUpperTrigram: z.string(),
  meihuaLowerTrigram: z.string(),
  meihuaMovingLine: z.string(),
  meihuaSource: z.string(),
  observationMode: z.string(),
  observationRegion: z.string(),
  observationDescriptor: z.string(),
  observationVisibility: z.string(),
  observationUncertainty: z.string(),
  selectionEventProfile: z.string(),
  selectionActions: z.string(),
  selectionStart: z.string(),
  selectionEnd: z.string(),
  selectionConstraints: z.string(),
  fengshuiPropertyScope: z.string(),
  fengshuiSelectedSchool: z.string(),
  fengshuiFacingDegrees: z.string(),
  fengshuiUncertaintyDegrees: z.string(),
  consent: z.boolean(),
  photoSelected: z.boolean(),
  observationNotes: z.string(),
  saveToArchive: z.boolean(),
  profile: z.string(),
  arts: z.array(z.string()),
  preference: z.string(),
  lines: z.array(z.string()),
});

export type TaskFormValues = z.infer<typeof taskSchemaBase>;

const defaultValues: TaskFormValues = {
  subject: "",
  calendar: "gregorian",
  birthDate: "",
  birthTime: "",
  targetYear: "",
  targetMonth: "",
  targetDate: "",
  unknownTime: false,
  location: "",
  timezone: "Asia/Shanghai",
  gender: "unspecified",
  timeStandard: "civil",
  longitude: "",
  latitude: "",
  coordinateSource: "",
  issue: "",
  focus: "",
  eventTime: "",
  divinationMethod: "coins",
  meihuaCastingMethod: "time",
  meihuaNumber: "",
  meihuaCount: "",
  meihuaUpperTrigram: "乾",
  meihuaLowerTrigram: "坤",
  meihuaMovingLine: "1",
  meihuaSource: "",
  observationMode: "face",
  observationRegion: "forehead",
  observationDescriptor: "region_visible",
  observationVisibility: "full",
  observationUncertainty: "0",
  selectionEventProfile: "business_opening_transaction",
  selectionActions: "开市",
  selectionStart: "",
  selectionEnd: "",
  selectionConstraints: "",
  fengshuiPropertyScope: "residential",
  fengshuiSelectedSchool: "bazhai",
  fengshuiFacingDegrees: "180",
  fengshuiUncertaintyDegrees: "0",
  consent: false,
  photoSelected: false,
  observationNotes: "",
  saveToArchive: false,
  profile: "",
  arts: [],
  preference: "direct",
  lines: ["", "", "", "", "", ""],
};

const taskErrorFields: Record<string, { id: string; label: string }> = {
  subject: { id: "subject", label: "受测对象" },
  birthDate: { id: "birth-date", label: "出生日期" },
  birthTime: { id: "birth-time", label: "出生时间" },
  targetYear: { id: "target-year", label: "流年目标年份" },
  targetMonth: { id: "target-month", label: "流月目标月份" },
  targetDate: { id: "target-date", label: "流日目标日期" },
  location: { id: "location", label: "出生地点" },
  timezone: { id: "timezone", label: "时区" },
  gender: { id: "gender", label: "性别" },
  calendar: { id: "calendar", label: "历法" },
  longitude: { id: "longitude", label: "出生经度" },
  latitude: { id: "latitude", label: "出生纬度" },
  coordinateSource: { id: "coordinate-source", label: "坐标来源" },
  issue: { id: "issue", label: "当前问题" },
  focus: { id: "focus", label: "判断侧重" },
  eventTime: { id: "event-time", label: "事件时间" },
  meihuaCastingMethod: { id: "meihua-casting-method", label: "梅花起卦方式" },
  meihuaNumber: { id: "meihua-number", label: "起卦数字" },
  meihuaCount: { id: "meihua-count", label: "声数" },
  meihuaUpperTrigram: { id: "meihua-upper-trigram", label: "上卦" },
  meihuaLowerTrigram: { id: "meihua-lower-trigram", label: "下卦" },
  meihuaMovingLine: { id: "meihua-moving-line", label: "动爻" },
  meihuaSource: { id: "meihua-source", label: "起法资料来源" },
  observationMode: { id: "observation-mode", label: "观照模式" },
  observationRegion: { id: "observation-region", label: "观察部位" },
  observationDescriptor: { id: "observation-descriptor", label: "观察描述" },
  observationVisibility: { id: "observation-visibility", label: "可见程度" },
  observationUncertainty: { id: "observation-uncertainty", label: "不确定度" },
  consent: { id: "consent", label: "照片处理独立同意" },
  photoSelected: { id: "file", label: "见相照片" },
  selectionEventProfile: { id: "selection-event-profile", label: "择日事件类型" },
  selectionActions: { id: "selection-actions", label: "择日行动" },
  selectionStart: { id: "selection-start", label: "择日开始日期" },
  selectionEnd: { id: "selection-end", label: "择日结束日期" },
  fengshuiPropertyScope: { id: "fengshui-property-scope", label: "空间类型" },
  fengshuiFacingDegrees: { id: "fengshui-facing-degrees", label: "朝向度数" },
  fengshuiUncertaintyDegrees: { id: "fengshui-uncertainty", label: "测量不确定度" },
  profile: { id: "profile", label: "立命资料" },
  arts: { id: "arts", label: "选择术数" },
  lines: { id: "line-0", label: "六次起卦过程" },
};

function firstLineErrorIndex(lineErrors: FieldErrors<TaskFormValues>["lines"]) {
  if (!Array.isArray(lineErrors)) return 0;
  const index = lineErrors.findIndex(Boolean);
  return index < 0 ? 0 : index;
}

function taskErrorField(productId: string, fieldName: string, errors?: FieldErrors<TaskFormValues>) {
  const field = taskErrorFields[fieldName];
  if (!field) return null;
  if (fieldName === "lines") {
    return { ...field, id: `${productId}-line-${firstLineErrorIndex(errors?.lines)}` };
  }
  return { ...field, id: `${productId}-${field.id}` };
}

function schemaFor(product: ProductDefinition) {
  const profileVersionIdPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return taskSchemaBase.superRefine((values, context) => {
    if (product.group === "natal") {
      if (!values.subject.trim()) context.addIssue({ code: "custom", path: ["subject"], message: "请填写受测对象" });
      if (!values.birthDate) context.addIssue({ code: "custom", path: ["birthDate"], message: "请选择出生日期" });
      if (!values.unknownTime && !values.birthTime) context.addIssue({ code: "custom", path: ["birthTime"], message: "请选择出生时间，或勾选时辰未知" });
      if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写出生地点" });

      if (["bazi", "luming-nayin", "ziwei", "qizheng"].includes(product.id)) {
        if (values.calendar !== "gregorian") {
          context.addIssue({ code: "custom", path: ["calendar"], message: "当前 Runtime 接口需要公历日期" });
        }
        if (values.unknownTime) {
          context.addIssue({ code: "custom", path: ["birthTime"], message: "当前核心盘面需要明确出生时间" });
        }
        if (values.gender === "unspecified") {
          context.addIssue({ code: "custom", path: ["gender"], message: "请确认性别后再建立盘面档案" });
        }
        if (!values.timezone.trim()) {
          context.addIssue({ code: "custom", path: ["timezone"], message: "请选择出生时区" });
        } else if (!isIanaTimeZone(values.timezone)) {
          context.addIssue({ code: "custom", path: ["timezone"], message: "请选择有效的 IANA 出生时区" });
        }
        const temporalTargetValues = [values.targetYear, values.targetMonth, values.targetDate].filter((value) => value.trim());
        if (["bazi", "ziwei", "qizheng"].includes(product.id) && temporalTargetValues.length > 1) {
          context.addIssue({ code: "custom", path: ["targetYear"], message: "目标年份、月份、日期只能三选一" });
        }
        if (["bazi", "ziwei", "qizheng"].includes(product.id) && values.targetYear.trim()) {
          const targetYear = Number(values.targetYear);
          if (!Number.isInteger(targetYear) || targetYear < 1800 || targetYear > 2199) {
            context.addIssue({ code: "custom", path: ["targetYear"], message: "流年目标年份必须是 1800 到 2199 的整数" });
          }
        }
        if (["bazi", "ziwei", "qizheng"].includes(product.id) && values.targetMonth.trim()) {
          const targetMonth = values.targetMonth.trim();
          const year = Number(targetMonth.slice(0, 4));
          if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(targetMonth) || !Number.isInteger(year) || year < 1800 || year > 2199) {
            context.addIssue({ code: "custom", path: ["targetMonth"], message: "流月目标月份必须是 1800-01 到 2199-12" });
          }
        }
        if (["bazi", "qizheng"].includes(product.id) && values.targetDate.trim()) {
          const targetDate = values.targetDate.trim();
          const year = Number(targetDate.slice(0, 4));
          const parsed = new Date(`${targetDate}T00:00:00Z`);
          if (!/^\d{4}-\d{2}-\d{2}$/.test(targetDate) || !Number.isInteger(year) || year < 1800 || year > 2199 || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== targetDate) {
            context.addIssue({ code: "custom", path: ["targetDate"], message: "流日目标日期必须是 1800-01-01 到 2199-12-31 的有效日期" });
          }
        }
        if (product.id === "ziwei" && values.targetDate.trim()) {
          context.addIssue({ code: "custom", path: ["targetDate"], message: "紫微当前支持流年或流月，不支持流日" });
        }
      }

      if (product.id === "qizheng") {
        const longitude = Number(values.longitude);
        const latitude = Number(values.latitude);
        if (!values.longitude.trim() || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
          context.addIssue({ code: "custom", path: ["longitude"], message: "七政需要 -180 到 180 之间的出生经度" });
        }
        if (!values.latitude.trim() || !Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
          context.addIssue({ code: "custom", path: ["latitude"], message: "七政需要 -90 到 90 之间的出生纬度" });
        }
        if (!values.coordinateSource.trim()) {
          context.addIssue({ code: "custom", path: ["coordinateSource"], message: "请说明坐标来源" });
        }
      }
    }

    if (product.group === "event" || product.id === "wenshi") {
      if (!values.issue.trim()) context.addIssue({ code: "custom", path: ["issue"], message: "请写清当前问题" });
      if (product.group === "event" && !values.focus) context.addIssue({ code: "custom", path: ["focus"], message: "请选择场景或侧重" });
      if (product.id !== "selection" && !values.eventTime) context.addIssue({ code: "custom", path: ["eventTime"], message: "请选择事件时空" });

      if (["liuyao", "meihua", "qimen", "daliuren", "wenshi", "taiyi", "selection"].includes(product.id)) {
        if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写事件地点" });
        if (!values.timezone.trim()) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择事件时区" });
        else if (!isIanaTimeZone(values.timezone)) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择有效的 IANA 事件时区" });
      }

      if (product.id === "selection") {
        if (!values.selectionEventProfile.trim()) context.addIssue({ code: "custom", path: ["selectionEventProfile"], message: "请选择择日事件类型" });
        if (!values.selectionActions.trim()) context.addIssue({ code: "custom", path: ["selectionActions"], message: "请填写至少一项择日行动" });
        if (!values.selectionStart) context.addIssue({ code: "custom", path: ["selectionStart"], message: "请选择开始日期" });
        if (!values.selectionEnd) context.addIssue({ code: "custom", path: ["selectionEnd"], message: "请选择结束日期" });
        if (values.selectionStart && values.selectionEnd && values.selectionEnd < values.selectionStart) context.addIssue({ code: "custom", path: ["selectionEnd"], message: "结束日期不能早于开始日期" });
      }

      if (product.id === "meihua") {
        const method = values.meihuaCastingMethod;
        if (method === "supplied_number") {
          if (!values.meihuaNumber.trim() || !Number.isInteger(Number(values.meihuaNumber)) || Number(values.meihuaNumber) <= 0) {
            context.addIssue({ code: "custom", path: ["meihuaNumber"], message: "请输入正整数起卦数字" });
          }
          if (!values.meihuaSource.trim()) context.addIssue({ code: "custom", path: ["meihuaSource"], message: "请说明数字资料来源" });
        } else if (method === "sound_count") {
          if (!values.meihuaCount.trim() || !Number.isInteger(Number(values.meihuaCount)) || Number(values.meihuaCount) <= 0) {
            context.addIssue({ code: "custom", path: ["meihuaCount"], message: "请输入正整数声数" });
          }
          if (!values.meihuaSource.trim()) context.addIssue({ code: "custom", path: ["meihuaSource"], message: "请说明声数观察来源" });
        } else if (method === "observation") {
          if (!values.meihuaUpperTrigram) context.addIssue({ code: "custom", path: ["meihuaUpperTrigram"], message: "请选择上卦" });
          if (!values.meihuaLowerTrigram) context.addIssue({ code: "custom", path: ["meihuaLowerTrigram"], message: "请选择下卦" });
          if (!values.meihuaSource.trim()) context.addIssue({ code: "custom", path: ["meihuaSource"], message: "请说明观察来源" });
        } else if (method === "supplied_hexagram") {
          if (!values.meihuaUpperTrigram) context.addIssue({ code: "custom", path: ["meihuaUpperTrigram"], message: "请选择上卦" });
          if (!values.meihuaLowerTrigram) context.addIssue({ code: "custom", path: ["meihuaLowerTrigram"], message: "请选择下卦" });
          const movingLine = Number(values.meihuaMovingLine);
          if (!Number.isInteger(movingLine) || movingLine < 1 || movingLine > 6) context.addIssue({ code: "custom", path: ["meihuaMovingLine"], message: "请选择 1 到 6 的动爻" });
          if (!values.meihuaSource.trim()) context.addIssue({ code: "custom", path: ["meihuaSource"], message: "请说明卦象资料来源" });
        }
      }
    }

    if (product.id === "jianxiang" && !values.consent) {
      context.addIssue({ code: "custom", path: ["consent"], message: "继续前需要作出独立同意" });
    }

    if (product.id === "jianxiang" && !values.photoSelected) {
      context.addIssue({ code: "custom", path: ["photoSelected"], message: "请选择一张照片" });
    }

    if (product.id === "jianxiang") {
      if (!values.subject.trim()) context.addIssue({ code: "custom", path: ["subject"], message: "请填写受测对象" });
      if (!values.observationRegion) context.addIssue({ code: "custom", path: ["observationRegion"], message: "请选择观察部位" });
      if (!values.observationDescriptor) context.addIssue({ code: "custom", path: ["observationDescriptor"], message: "请选择观察描述" });
      const uncertainty = Number(values.observationUncertainty);
      if (!Number.isFinite(uncertainty) || uncertainty < 0 || uncertainty > 1) {
        context.addIssue({ code: "custom", path: ["observationUncertainty"], message: "不确定度必须在 0 到 1 之间" });
      }
    }

    if (product.id === "fengshui") {
      if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写空间所在地点" });
      const facing = Number(values.fengshuiFacingDegrees);
      const uncertainty = Number(values.fengshuiUncertaintyDegrees);
      if (!Number.isFinite(facing) || facing < 0 || facing >= 360) context.addIssue({ code: "custom", path: ["fengshuiFacingDegrees"], message: "朝向度数必须在 0 到 359.99 之间" });
      if (!Number.isFinite(uncertainty) || uncertainty < 0 || uncertainty > 180) context.addIssue({ code: "custom", path: ["fengshuiUncertaintyDegrees"], message: "测量不确定度必须在 0 到 180 之间" });
    }

    if (product.id === "hecan") {
      if (!values.profile.trim()) {
        context.addIssue({ code: "custom", path: ["profile"], message: "请输入已确认 ProfileVersion ID" });
      } else if (!profileVersionIdPattern.test(values.profile.trim())) {
        context.addIssue({ code: "custom", path: ["profile"], message: "请输入有效的 ProfileVersion UUID" });
      }
      if (values.arts.length < 2) context.addIssue({ code: "custom", path: ["arts"], message: "至少选择两术" });
      if (!values.arts.includes("八字")) context.addIssue({ code: "custom", path: ["arts"], message: "当前结构接入要求八字为主术，请至少再选择一术" });
    }

    if (product.id === "canwen") {
      if (!values.issue.trim()) context.addIssue({ code: "custom", path: ["issue"], message: "请写清当前问题" });
      if (!values.profile.trim()) {
        context.addIssue({ code: "custom", path: ["profile"], message: "请输入已确认 ProfileVersion ID" });
      } else if (!profileVersionIdPattern.test(values.profile.trim())) {
        context.addIssue({ code: "custom", path: ["profile"], message: "请输入有效的 ProfileVersion UUID" });
      }
      if (values.arts.length < 2) context.addIssue({ code: "custom", path: ["arts"], message: "至少选择两术" });
      if (!values.arts.includes("八字")) context.addIssue({ code: "custom", path: ["arts"], message: "当前结构接入要求八字为主术，请至少再选择一术" });
    }

    if (product.id === "liuyao" || product.id === "wenshi") {
      values.lines.forEach((line, index) => {
        if (!line) {
          context.addIssue({
            code: "custom",
            path: ["lines", index],
            message: index === 0 ? "请完成六次起卦过程" : `请选择第 ${index + 1} 次起卦结果`,
          });
        }
      });
    }
  });
}

type FieldProps = {
  label: string;
  htmlFor: string;
  help?: string;
  error?: string;
  children: React.ReactNode;
};

type JianxiangCaptureState = "empty" | "selected" | "quality-unavailable" | "deleted";

const FACE_DESCRIPTOR_OPTIONS: Record<string, readonly string[]> = {
  forehead: ["region_visible", "relative_width_broad", "relative_width_narrow", "contour_rounded", "contour_flat"],
  left_eyebrow: ["region_visible", "line_straight", "line_curved", "density_even", "density_sparse_visible"],
  right_eyebrow: ["region_visible", "line_straight", "line_curved", "density_even", "density_sparse_visible"],
  left_eye: ["region_visible", "aperture_open", "aperture_narrow", "alignment_level"],
  right_eye: ["region_visible", "aperture_open", "aperture_narrow", "alignment_level"],
  nose: ["region_visible", "bridge_straight", "tip_rounded", "relative_width_broad", "relative_width_narrow"],
  mouth: ["region_visible", "lip_line_straight", "lip_line_curved", "mouth_closed", "mouth_open"],
  chin: ["region_visible", "contour_rounded", "contour_square", "contour_pointed"],
  jawline: ["region_visible", "outline_rounded", "outline_angular"],
  left_ear: ["region_visible", "outline_visible", "partially_visible"],
  right_ear: ["region_visible", "outline_visible", "partially_visible"],
  left_cheek: ["region_visible", "contour_full_relative", "contour_flat_relative"],
  right_cheek: ["region_visible", "contour_full_relative", "contour_flat_relative"],
  complexion: ["region_visible"],
};

const PALM_DESCRIPTOR_OPTIONS: Record<string, readonly string[]> = {
  left_palm: ["region_visible", "ridge_visible", "texture_even_visible"],
  right_palm: ["region_visible", "ridge_visible", "texture_even_visible"],
  life_line: ["region_visible", "line_continuous", "line_discontinuous", "line_deep_visible", "line_shallow_visible"],
  head_line: ["region_visible", "line_continuous", "line_discontinuous", "line_deep_visible", "line_shallow_visible"],
  heart_line: ["region_visible", "line_continuous", "line_discontinuous", "line_deep_visible", "line_shallow_visible"],
  fate_line: ["region_visible", "line_continuous", "line_discontinuous", "line_deep_visible", "line_shallow_visible"],
};

const POSTURE_DESCRIPTOR_OPTIONS: Record<string, readonly string[]> = {
  head_posture: ["region_visible", "level", "forward_tilt", "backward_tilt"],
  shoulder_line: ["region_visible", "level", "uneven"],
  spine_curve: ["region_visible", "aligned", "curved"],
  walking_gait: ["region_visible", "steady", "uneven"],
  sitting_posture: ["region_visible", "upright", "forward_lean", "uneven"],
};

const OBSERVATION_OPTIONS: Record<string, Record<string, readonly string[]>> = {
  face: FACE_DESCRIPTOR_OPTIONS,
  palm: PALM_DESCRIPTOR_OPTIONS,
  posture: POSTURE_DESCRIPTOR_OPTIONS,
  combined: { ...FACE_DESCRIPTOR_OPTIONS, ...PALM_DESCRIPTOR_OPTIONS, ...POSTURE_DESCRIPTOR_OPTIONS },
};

function Field({ label, htmlFor, help, error, children }: FieldProps) {
  const helpId = help ? `${htmlFor}-help` : undefined;
  const errorId = error ? `${htmlFor}-error` : undefined;
  return (
    <div className={styles.field}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {help ? <p id={helpId}>{help}</p> : null}
      {error ? <p className={styles.error} id={errorId} role="alert">{error}</p> : null}
    </div>
  );
}

function ChoiceGroup({
  id,
  legend,
  help,
  error,
  children,
}: {
  id?: string;
  legend: string;
  help?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className={styles.choiceGroup} id={id} tabIndex={id ? -1 : undefined}>
      <legend>{legend}</legend>
      {help ? <p>{help}</p> : null}
      <div className={styles.choices}>{children}</div>
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </fieldset>
  );
}

export function ProductInputForm({
  product,
  initialValues,
  onConfirm,
  onPhotoChange,
}: {
  product: ProductDefinition;
  initialValues?: TaskFormValues;
  onConfirm: (values: TaskFormValues) => void;
  onPhotoChange?: (file: File | null) => void;
}) {
  const schema = useMemo(() => schemaFor(product), [product]);
  const {
    control,
    formState: { errors },
    handleSubmit,
    register,
    setValue,
  } = useForm<TaskFormValues>({
    resolver: zodResolver(schema),
    defaultValues: initialValues ?? defaultValues,
    mode: "onSubmit",
    shouldFocusError: false,
  });
  const unknownTime = useWatch({ control, name: "unknownTime" });
  const meihuaCastingMethod = useWatch({ control, name: "meihuaCastingMethod" });
  const observationMode = useWatch({ control, name: "observationMode" });
  const observationRegion = useWatch({ control, name: "observationRegion" });
  const observationOptions = OBSERVATION_OPTIONS[observationMode] ?? FACE_DESCRIPTOR_OPTIONS;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [captureState, setCaptureState] = useState<JianxiangCaptureState>("empty");
  const [photoName, setPhotoName] = useState("");
  const validationErrors = Object.keys(errors)
    .map((fieldName) => taskErrorField(product.id, fieldName, errors))
    .filter((field): field is { id: string; label: string } => Boolean(field));
  const handleInvalid = (invalidErrors: FieldErrors<TaskFormValues>) => {
    const invalidFieldNames = Object.keys(invalidErrors);
    const firstErrorFieldName = (product.id === "jianxiang" && invalidErrors.photoSelected
      ? ["photoSelected", ...invalidFieldNames.filter((fieldName) => fieldName !== "photoSelected")]
      : invalidFieldNames)
      .map((fieldName) => ({
        fieldName,
        field: taskErrorField(product.id, fieldName, invalidErrors),
      }))
      .find(({ field }) => Boolean(field));
    if (!firstErrorFieldName?.field) return;
    const targetId = firstErrorFieldName.fieldName === "photoSelected" && product.id === "jianxiang"
      ? "jianxiang-file"
      : firstErrorFieldName.field.id;
    document.getElementById(targetId)?.focus();
  };
  const handlePhotoChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    setPhotoName(file.name);
    setCaptureState("selected");
    onPhotoChange?.(file);
    setValue("photoSelected", true, { shouldDirty: true, shouldValidate: true });
  };
  const clearPhoto = () => {
    setPhotoName("");
    setCaptureState("deleted");
    onPhotoChange?.(null);
    setValue("photoSelected", false, { shouldDirty: true, shouldValidate: true });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <form aria-label={`${product.name}任务输入`} className={styles.formPanel} noValidate onSubmit={handleSubmit(onConfirm, handleInvalid)}>
      <div className={styles.formHeader}>
        <div>
          <h2>{product.name}任务输入</h2>
          <p>只填写本任务需要的资料。带“必填”的项目会在本机先检查。</p>
        </div>
        <span><Info aria-hidden="true" size={16} /> {["bazi", "luming-nayin", "ziwei", "qizheng", "liuyao", "meihua", "qimen", "daliuren", "taiyi", "selection", "wenshi", "jianxiang", "fengshui"].includes(product.id) ? "确认后提交到对应计算服务" : "当前不会提交到计算服务"}</span>
      </div>

      {validationErrors.length > 0 ? (
        <div
          aria-labelledby={`${product.id}-error-summary-title`}
          className={styles.errorSummary}
          role="alert"
        >
          <h3 id={`${product.id}-error-summary-title`}>请先修正以下输入</h3>
          <ul>
            {validationErrors.map((field) => (
              <li key={field.id}>
                <a href={`#${field.id}`}>{field.label}</a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {product.group === "natal" ? (
        <fieldset className={styles.fieldGroup}>
          <legend>出生资料</legend>
          <Field htmlFor={`${product.id}-subject`} label="受测对象" error={errors.subject?.message} help="可以填写“本人”或便于自己识别的称呼。">
            <input id={`${product.id}-subject`} aria-describedby={errors.subject ? `${product.id}-subject-error` : `${product.id}-subject-help`} autoComplete="name" {...register("subject")} />
          </Field>
          <div className={styles.twoColumns}>
            <Field htmlFor={`${product.id}-calendar`} label="历法">
              <select id={`${product.id}-calendar`} {...register("calendar")}>
                <option value="gregorian">公历</option>
                <option disabled={["bazi", "luming-nayin", "ziwei", "qizheng"].includes(product.id)} value="lunar">农历</option>
              </select>
            </Field>
            <Field htmlFor={`${product.id}-gender`} label="性别">
              <select id={`${product.id}-gender`} {...register("gender")}>
                <option value="unspecified">暂不指定</option>
                <option value="female">女</option>
                <option value="male">男</option>
              </select>
            </Field>
          </div>
          <div className={styles.twoColumns}>
            <Field htmlFor={`${product.id}-birth-date`} label="出生日期" error={errors.birthDate?.message}>
              <input id={`${product.id}-birth-date`} type="date" aria-describedby={errors.birthDate ? `${product.id}-birth-date-error` : undefined} {...register("birthDate")} />
            </Field>
            <Field htmlFor={`${product.id}-birth-time`} label="出生时间" error={errors.birthTime?.message} help={unknownTime ? "已标记时辰未知，不会要求填写具体时间。" : "请按当时民用钟表时间填写。"}>
              <input id={`${product.id}-birth-time`} type="time" disabled={unknownTime} aria-describedby={errors.birthTime ? `${product.id}-birth-time-error` : `${product.id}-birth-time-help`} {...register("birthTime")} />
            </Field>
          </div>
          <label className={styles.checkRow}>
            <input id={`${product.id}-unknown-time`} type="checkbox" {...register("unknownTime")} />
            <span><strong>未知时辰</strong><small>后续只开放支持未知时辰的能力，并明确精度边界。</small></span>
          </label>
          <Field htmlFor={`${product.id}-location`} label="出生地点" error={errors.location?.message} help="用于确定时区与地方时口径；当前只做输入确认。">
            <input id={`${product.id}-location`} aria-describedby={errors.location ? `${product.id}-location-error` : `${product.id}-location-help`} autoComplete="address-level2" placeholder="省 / 市 / 区县" {...register("location")} />
          </Field>
          <Field htmlFor={`${product.id}-timezone`} label="出生时区" error={errors.timezone?.message} help="主动确认出生地的 IANA 时区，不读取设备位置。">
            <input id={`${product.id}-timezone`} aria-describedby={errors.timezone ? `${product.id}-timezone-error` : `${product.id}-timezone-help`} autoComplete="off" list={`${product.id}-timezone-options`} placeholder="例如 Asia/Shanghai" {...register("timezone")} />
            <IanaTimeZoneOptions id={`${product.id}-timezone-options`} />
          </Field>
          <Field htmlFor={`${product.id}-time-standard`} label="时间口径" help="默认民用钟表时间；当地视太阳时由确定性脚本换算。">
            <select id={`${product.id}-time-standard`} {...register("timeStandard")}>
              <option value="civil">民用钟表时间</option>
              <option value="local-apparent-solar">当地视太阳时</option>
            </select>
          </Field>
          <ProductSpecificNatalOptions errors={errors} product={product} register={register} />
        </fieldset>
      ) : null}

      {product.group === "event" || product.id === "wenshi" ? (
        <fieldset className={styles.fieldGroup}>
          <legend>{product.id === "wenshi" ? "同一问题与时空" : "问题与事件时空"}</legend>
          <Field htmlFor={`${product.id}-issue`} label={product.id === "wenshi" ? "同一问题" : "当前问题"} error={errors.issue?.message} help="只写一件事，说明对象、目标和希望判断的时间范围。">
            <textarea id={`${product.id}-issue`} rows={4} aria-describedby={errors.issue ? `${product.id}-issue-error` : `${product.id}-issue-help`} {...register("issue")} />
          </Field>
          {product.id !== "wenshi" ? (
            <Field htmlFor={`${product.id}-focus`} label={product.id === "liuyao" ? "起卦方式" : product.id === "qimen" ? "场景侧重" : "判断侧重"} error={errors.focus?.message}>
              <select id={`${product.id}-focus`} aria-describedby={errors.focus ? `${product.id}-focus-error` : undefined} {...register("focus")}>
                <option value="">请选择</option>
                {product.id === "liuyao" ? <><option value="coins">三枚硬币</option><option value="manual">手动记录</option></> : null}
                {product.id === "meihua" ? <><option value="outcome">结果观察</option><option value="state">状态变化</option></> : null}
                {product.id === "qimen" ? <><option value="action">行动选择</option><option value="situation">局势判断</option><option value="timing">时机观察</option></> : null}
                {product.id === "daliuren" ? <><option value="progress">事情进展</option><option value="people">人事关系</option><option value="outcome">结果观察</option></> : null}
                {product.id === "taiyi" ? <><option value="outcome">年度结果</option><option value="timing">时间节律</option><option value="location">空间范围</option><option value="state">结构状态</option></> : null}
                {product.id === "selection" ? <><option value="timing">时间排序</option><option value="state">候选状态</option><option value="location">方位条件</option></> : null}
              </select>
            </Field>
          ) : null}
          {product.id !== "selection" ? (
            <Field htmlFor={`${product.id}-event-time`} label={product.id === "wenshi" ? "同一事件时空" : product.id === "taiyi" ? "参考时间" : "事件时间"} error={errors.eventTime?.message} help="默认使用你明确选择的当地时间，不读取设备位置。">
              <input id={`${product.id}-event-time`} type="datetime-local" aria-describedby={errors.eventTime ? `${product.id}-event-time-error` : `${product.id}-event-time-help`} {...register("eventTime")} />
            </Field>
          ) : null}
          {["liuyao", "meihua", "qimen", "daliuren", "wenshi", "taiyi", "selection"].includes(product.id) ? (
            <>
              <Field htmlFor={`${product.id}-timezone`} label="事件时区" error={errors.timezone?.message} help="主动确认事件发生地的 IANA 时区，不读取设备位置。">
                <input id={`${product.id}-timezone`} aria-describedby={errors.timezone ? `${product.id}-timezone-error` : `${product.id}-timezone-help`} autoComplete="off" list={`${product.id}-timezone-options`} placeholder="例如 Asia/Shanghai" {...register("timezone")} />
                <IanaTimeZoneOptions id={`${product.id}-timezone-options`} />
              </Field>
              <Field htmlFor={`${product.id}-location`} label="事件地点" error={errors.location?.message} help="用于保留起局/起课的地点事实。">
                <input id={`${product.id}-location`} aria-describedby={errors.location ? `${product.id}-location-error` : `${product.id}-location-help`} autoComplete="address-level2" placeholder="省 / 市 / 区县" {...register("location")} />
              </Field>
          {product.id !== "liuyao" ? (
                <Field htmlFor={`${product.id}-time-standard`} label="事件时间口径" help="默认民用钟表时间；需要真太阳时时再明确选择。">
                  <select id={`${product.id}-time-standard`} {...register("timeStandard")}>
                    <option value="civil">民用钟表时间</option>
                    <option value="local-apparent-solar">当地视太阳时</option>
                  </select>
                </Field>
              ) : null}
            </>
          ) : null}
          {product.id === "selection" ? (
            <>
              <div className={styles.twoColumns}>
                <Field htmlFor="selection-start" label="开始日期" error={errors.selectionStart?.message}>
                  <input id="selection-start" type="date" {...register("selectionStart")} />
                </Field>
                <Field htmlFor="selection-end" label="结束日期" error={errors.selectionEnd?.message}>
                  <input id="selection-end" type="date" {...register("selectionEnd")} />
                </Field>
              </div>
              <Field htmlFor="selection-event-profile" label="事件类型" error={errors.selectionEventProfile?.message}>
                <select id="selection-event-profile" {...register("selectionEventProfile")}>
                  <option value="business_opening_transaction">开市 / 交易</option>
                  <option value="moving_residence">搬迁 / 入宅</option>
                  <option value="contract_signing">签约 / 合作</option>
                  <option value="generic_selection">其他择日</option>
                </select>
              </Field>
              <Field htmlFor="selection-actions" label="计划行动" error={errors.selectionActions?.message} help="多个行动用逗号分隔，系统不会从长文本猜测行动。">
                <input id="selection-actions" {...register("selectionActions")} placeholder="例如：开市" />
              </Field>
              <Field htmlFor="selection-constraints" label="硬约束" help="只记录你明确提出的约束，不自动把偏好变成硬条件。">
                <input id="selection-constraints" {...register("selectionConstraints")} placeholder="例如：避开周末" />
              </Field>
            </>
          ) : null}
          {product.id === "meihua" ? (
            <>
              <Field htmlFor="meihua-casting-method" label="梅花起卦方式" error={errors.meihuaCastingMethod?.message} help="按实际采用的起法提交，不会把数字、声音或观测资料改成时间起卦。">
                <select id="meihua-casting-method" {...register("meihuaCastingMethod")}>
                  <option value="time">按时间起卦</option>
                  <option value="supplied_number">按数字起卦</option>
                  <option value="sound_count">按声数起卦</option>
                  <option value="observation">按观察起卦</option>
                  <option value="supplied_hexagram">提供完整卦象</option>
                </select>
              </Field>
              {meihuaCastingMethod === "supplied_number" ? (
                <>
                  <Field htmlFor="meihua-number" label="起卦数字" error={errors.meihuaNumber?.message}>
                    <input id="meihua-number" type="number" min="1" step="1" {...register("meihuaNumber")} />
                  </Field>
                  <Field htmlFor="meihua-source" label="数字资料来源" error={errors.meihuaSource?.message} help="只记录来源，不让系统从自然语言自行猜卦。">
                    <input id="meihua-source" {...register("meihuaSource")} placeholder="例如：用户现场报数" />
                  </Field>
                </>
              ) : null}
              {meihuaCastingMethod === "sound_count" ? (
                <>
                  <Field htmlFor="meihua-count" label="声数" error={errors.meihuaCount?.message}>
                    <input id="meihua-count" type="number" min="1" step="1" {...register("meihuaCount")} />
                  </Field>
                  <Field htmlFor="meihua-source" label="声数观察来源" error={errors.meihuaSource?.message}>
                    <input id="meihua-source" {...register("meihuaSource")} placeholder="例如：现场声音计数" />
                  </Field>
                </>
              ) : null}
              {meihuaCastingMethod === "observation" || meihuaCastingMethod === "supplied_hexagram" ? (
                <>
                  <div className={styles.twoColumns}>
                    <Field htmlFor="meihua-upper-trigram" label="上卦" error={errors.meihuaUpperTrigram?.message}>
                      <select id="meihua-upper-trigram" {...register("meihuaUpperTrigram")}>
                        {(["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"] as const).map((trigram) => <option key={trigram} value={trigram}>{trigram}</option>)}
                      </select>
                    </Field>
                    <Field htmlFor="meihua-lower-trigram" label="下卦" error={errors.meihuaLowerTrigram?.message}>
                      <select id="meihua-lower-trigram" {...register("meihuaLowerTrigram")}>
                        {(["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"] as const).map((trigram) => <option key={trigram} value={trigram}>{trigram}</option>)}
                      </select>
                    </Field>
                  </div>
                  {meihuaCastingMethod === "supplied_hexagram" ? (
                    <Field htmlFor="meihua-moving-line" label="动爻" error={errors.meihuaMovingLine?.message}>
                      <select id="meihua-moving-line" {...register("meihuaMovingLine")}>
                        {[1, 2, 3, 4, 5, 6].map((line) => <option key={line} value={line}>{line} 爻</option>)}
                      </select>
                    </Field>
                  ) : null}
                  <Field htmlFor="meihua-source" label={meihuaCastingMethod === "observation" ? "观察来源" : "卦象资料来源"} error={errors.meihuaSource?.message}>
                    <input id="meihua-source" {...register("meihuaSource")} placeholder="例如：用户现场记录" />
                  </Field>
                </>
              ) : null}
            </>
          ) : null}
          {product.id === "liuyao" || product.id === "wenshi" ? (
            <SixLineProcess
              errors={errors.lines}
              productId={product.id}
              register={register}
            />
          ) : null}
        </fieldset>
      ) : null}

      {product.id === "jianxiang" ? (
        <fieldset className={styles.fieldGroup}>
          <legend>采集模式与独立同意</legend>
          <Field htmlFor="jianxiang-subject" label="受测对象" error={errors.subject?.message} help="只填写本人或已获授权的对象称呼；不从照片猜测身份。">
            <input id="jianxiang-subject" autoComplete="name" {...register("subject")} placeholder="例如：本人" />
          </Field>
          <Field htmlFor="jianxiang-mode" label="观照模式" help="四种模式都只接收你核对过的可见观察；系统不会从原图猜测结论。">
            <select
              id="jianxiang-mode"
              {...register("observationMode", {
                onChange: (event) => {
                  const nextMode = event.target.value as string;
                  const nextRegions = Object.keys(OBSERVATION_OPTIONS[nextMode] ?? FACE_DESCRIPTOR_OPTIONS);
                  const nextRegion = nextRegions[0] ?? "forehead";
                  setValue("observationRegion", nextRegion, { shouldDirty: true, shouldValidate: true });
                  setValue("observationDescriptor", OBSERVATION_OPTIONS[nextMode]?.[nextRegion]?.[0] ?? "region_visible", { shouldDirty: true, shouldValidate: true });
                },
              })}
            >
              <option value="face">面相</option>
              <option value="palm">手相</option>
              <option value="posture">体态</option>
              <option value="combined">综合观照</option>
            </select>
          </Field>
          <fieldset className={styles.fieldGroup}>
            <legend>已核对的结构化观察</legend>
            <p>原图不会被 Runtime 读取；请只提交你已经核对、且能说明可见程度的观察，不让系统从照片自动猜测。</p>
            <div className={styles.twoColumns}>
              <Field htmlFor="jianxiang-observation-region" label="观察部位" error={errors.observationRegion?.message}>
                <select
                  id="jianxiang-observation-region"
                  {...register("observationRegion", {
                    onChange: (event) => {
                      const nextRegion = event.target.value as string;
                      setValue("observationDescriptor", observationOptions[nextRegion]?.[0] ?? "region_visible", { shouldDirty: true, shouldValidate: true });
                    },
                  })}
                >
                  {Object.keys(observationOptions).map((region) => <option key={region} value={region}>{region}</option>)}
                </select>
              </Field>
              <Field htmlFor="jianxiang-observation-descriptor" label="观察描述" error={errors.observationDescriptor?.message}>
                <select id="jianxiang-observation-descriptor" {...register("observationDescriptor")}>
                  {(observationOptions[observationRegion] ?? ["region_visible"]).map((descriptor) => <option key={descriptor} value={descriptor}>{descriptor}</option>)}
                </select>
              </Field>
            </div>
            <div className={styles.twoColumns}>
              <Field htmlFor="jianxiang-observation-visibility" label="可见程度" error={errors.observationVisibility?.message}>
                <select id="jianxiang-observation-visibility" {...register("observationVisibility")}>
                  <option value="full">完整可见</option>
                  <option value="partial">部分可见</option>
                </select>
              </Field>
              <Field htmlFor="jianxiang-observation-uncertainty" label="不确定度" error={errors.observationUncertainty?.message} help="0 表示你确认度最高，1 表示几乎无法确认。">
                <input id="jianxiang-observation-uncertainty" type="number" min="0" max="1" step="0.05" {...register("observationUncertainty")} />
              </Field>
            </div>
          </fieldset>
          <label className={styles.consentRow} htmlFor="jianxiang-consent">
            <input id="jianxiang-consent" type="checkbox" {...register("consent")} />
            <span><strong>照片处理独立同意</strong><small>我已了解原图、结构化观察和命理解读是三层不同数据，并可在提交前删除。</small></span>
          </label>
          {errors.consent ? <p className={styles.error} role="alert">{errors.consent.message}</p> : null}
          <label className={styles.consentRow} htmlFor="jianxiang-save-to-archive">
            <input id="jianxiang-save-to-archive" type="checkbox" {...register("saveToArchive")} />
            <span><strong>保存到见相档案（另行同意）</strong><small>未勾选时只保留本次任务所需的短期媒体；当前页面不会执行保存。</small></span>
          </label>
          <div className={styles.capturePanel}>
            <div><Camera aria-hidden="true" size={22} /><strong>拍摄或上传照片</strong></div>
            <p id="jianxiang-file-help">相机被拒绝时始终可选文件。确认后文件才会上传到本次私有会话，并按页面显示的期限自动过期。</p>
            <Status state="unavailable" title="相机采集待接入" description="当前环境不会请求相机权限；请使用本地文件入口，拒绝权限不影响任务输入。" />
            <Status state="success" title="服务端质量检查已接入" description="确认后服务端会读取容器尺寸和格式；不满足条件时不会建立资产。" />
            {captureState === "quality-unavailable" ? (
              <Status state="unavailable" title="照片质量检查待接入" description="当前页面只记录本地选择；确认后才由服务端检查容器尺寸和格式。" />
            ) : null}
            {captureState === "selected" ? (
              <p aria-label="已选择本地照片" aria-live="polite" role="status">已选择本地照片：{photoName}</p>
            ) : captureState === "deleted" ? (
              <p aria-label="本地照片已删除" aria-live="polite" role="status">本地照片已删除，可重新选择。</p>
            ) : (
              <p aria-label="尚未选择照片" aria-live="polite" role="status">尚未选择照片。</p>
            )}
            {errors.photoSelected ? <p className={styles.error} id="jianxiang-file-error" role="alert">{errors.photoSelected.message}</p> : null}
            <div className={styles.captureActions}>
              <label className={styles.fileButton} htmlFor="jianxiang-file">
                <Upload aria-hidden="true" size={16} /> {photoName ? "重新选择照片" : "选择见相照片"}
              </label>
              {photoName ? (
                <>
                  <button className={styles.secondaryButton} onClick={() => setCaptureState("quality-unavailable")} type="button">检查照片质量</button>
                  <button className={styles.secondaryButton} onClick={clearPhoto} type="button">删除本地照片</button>
                </>
              ) : null}
            </div>
            <input
              ref={fileInputRef}
              aria-describedby={errors.photoSelected ? "jianxiang-file-help jianxiang-file-error" : "jianxiang-file-help"}
              aria-invalid={errors.photoSelected ? "true" : undefined}
              className={styles.visuallyHidden}
              id="jianxiang-file"
              onChange={handlePhotoChange}
              type="file"
              accept="image/jpeg,image/png,image/heic"
            />
          </div>
          <Field htmlFor="jianxiang-observation-notes" label="用户补充信息" help="照片无法确定的步态、声音或背景信息必须由用户明确补充，不由系统猜测。">
            <textarea id="jianxiang-observation-notes" rows={4} {...register("observationNotes")} />
          </Field>
        </fieldset>
      ) : null}

      {product.id === "fengshui" ? (
        <fieldset className={styles.fieldGroup}>
          <legend>空间与罗盘测量</legend>
          <Field htmlFor="fengshui-location" label="空间所在地点" error={errors.location?.message} help="只记录用户确认的地点，不读取设备定位。">
            <input id="fengshui-location" autoComplete="address-level2" {...register("location")} placeholder="省 / 市 / 区县" />
          </Field>
          <div className={styles.twoColumns}>
            <Field htmlFor="fengshui-property-scope" label="空间类型" error={errors.fengshuiPropertyScope?.message}>
              <select id="fengshui-property-scope" {...register("fengshuiPropertyScope")}>
                <option value="residential">住宅</option>
                <option value="workplace">办公 / 店铺</option>
              </select>
            </Field>
            <Field htmlFor="fengshui-school" label="理气学校">
              <select id="fengshui-school" {...register("fengshuiSelectedSchool")}>
                <option value="bazhai">八宅</option>
              </select>
            </Field>
          </div>
          <div className={styles.twoColumns}>
            <Field htmlFor="fengshui-facing-degrees" label="入口朝向（度）" error={errors.fengshuiFacingDegrees?.message} help="以真北为 0°，顺时针填写 0–359.99°。">
              <input id="fengshui-facing-degrees" type="number" min="0" max="359.99" step="0.01" {...register("fengshuiFacingDegrees")} />
            </Field>
            <Field htmlFor="fengshui-uncertainty" label="测量不确定度（度）" error={errors.fengshuiUncertaintyDegrees?.message}>
              <input id="fengshui-uncertainty" type="number" min="0" max="180" step="0.1" {...register("fengshuiUncertaintyDegrees")} />
            </Field>
          </div>
          <Field htmlFor="fengshui-notes" label="空间观察补充" help="只写已经看到或测到的事实；不在此处直接写吉凶结论。">
            <textarea id="fengshui-notes" rows={4} {...register("observationNotes")} />
          </Field>
        </fieldset>
      ) : null}

      {product.id === "hecan" || product.id === "canwen" ? (
        <fieldset className={styles.fieldGroup}>
          <legend>{product.id === "hecan" ? "立命与择术" : "问题、立命与表达"}</legend>
          {product.id === "canwen" ? (
            <Field htmlFor="canwen-issue" label="当前问题" error={errors.issue?.message}>
              <textarea id="canwen-issue" rows={4} {...register("issue")} />
            </Field>
          ) : null}
          <Field htmlFor={`${product.id}-profile`} label="立命资料" error={errors.profile?.message} help="请输入已确认 ProfileVersion ID（UUID）；不会用名称或占位文字代替真实出生档案。">
            <input id={`${product.id}-profile`} aria-describedby={errors.profile ? `${product.id}-profile-error` : `${product.id}-profile-help`} {...register("profile")} />
          </Field>
          <ChoiceGroup id={`${product.id}-arts`} legend={product.id === "hecan" ? "至少选择两术（八字为主术，至少再选一术）" : "选择命盘"} help={product.id === "hecan" ? "当前结构接入固定八字为主术，再从紫微、七政中选择；各术结果不会被平均成一段话。" : "当前结构接入固定八字为主术，再选择需要参证的命盘。"} error={errors.arts?.message}>
            {(["八字", "紫微", "七政"] as const).map((art) => (
              <label className={styles.choiceCard} key={art}>
                <input type="checkbox" value={art} {...register("arts")} />
                <span><strong>{art}</strong><small>{art === "八字" ? "时间结构" : art === "紫微" ? "宫位参证" : "星曜参证"}</small></span>
              </label>
            ))}
          </ChoiceGroup>
          {product.id === "canwen" ? (
            <Field htmlFor="canwen-preference" label="表达偏好" help="只改变组织方式，不改变盘面事实。">
              <select id="canwen-preference" {...register("preference")}>
                <option value="direct">先给结论</option>
                <option value="evidence">先看依据</option>
                <option value="questions">按问题拆解</option>
              </select>
            </Field>
          ) : null}
        </fieldset>
      ) : null}

      <button className={styles.primaryButton} type="submit">检查输入</button>
      <p className={styles.submitNote}>{["bazi", "luming-nayin", "ziwei", "qizheng", "hecan", "canwen", "liuyao", "meihua", "qimen", "daliuren", "taiyi", "selection", "fengshui", "wenshi"].includes(product.id) ? "确认后会提交到对应 Runtime 盘面服务，并跳转到私有结果页；只生成确定性盘面，不在浏览器计算。" : "检查只发生在当前页面。继续后会在工作台明确显示未接入能力，不扣权益。"}</p>
    </form>
  );
}

function ProductSpecificNatalOptions({
  errors,
  product,
  register,
}: {
  errors: FieldErrors<TaskFormValues>;
  product: ProductDefinition;
  register: UseFormRegister<TaskFormValues>;
}) {
  if (product.id === "bazi") return (
    <>
      <p className={styles.productNote}>八字专有：后续可分别确认真太阳时换算、早晚子时与换日规则；目标时间层只选一个。</p>
      <TemporalTargetFields errors={errors} productId="bazi" register={register} supportsDay />
    </>
  );
  if (product.id === "ziwei") return (
    <>
      <p className={styles.productNote}>紫微专有：后续会单独确认闰月、命宫起法与四化版本；目标时间层只选一个。</p>
      <TemporalTargetFields errors={errors} productId="ziwei" register={register} />
    </>
  );
  if (product.id === "qizheng") return (
    <>
      <p className={styles.productNote}>七政专有：地点将用于经纬度与时区校准，并保留坐标来源。</p>
      <TemporalTargetFields errors={errors} productId="qizheng" register={register} supportsDay />
      <div className={styles.twoColumns}>
        <Field htmlFor="qizheng-longitude" label="出生经度" error={errors.longitude?.message} help="东经为正，西经为负。">
          <input id="qizheng-longitude" inputMode="decimal" {...register("longitude")} />
        </Field>
        <Field htmlFor="qizheng-latitude" label="出生纬度" error={errors.latitude?.message} help="北纬为正，南纬为负。">
          <input id="qizheng-latitude" inputMode="decimal" {...register("latitude")} />
        </Field>
      </div>
      <Field htmlFor="qizheng-coordinate-source" label="坐标来源" error={errors.coordinateSource?.message} help="例如城市地理编码、用户确认。">
        <input id="qizheng-coordinate-source" {...register("coordinateSource")} />
      </Field>
    </>
  );
  return null;
}

function TargetYearField({
  errors,
  productId,
  register,
}: {
  errors: FieldErrors<TaskFormValues>;
  productId: "bazi" | "ziwei" | "qizheng";
  register: UseFormRegister<TaskFormValues>;
}) {
  return (
    <Field
      htmlFor={`${productId}-target-year`}
      label="流年目标年份（可选）"
      error={errors.targetYear?.message}
      help="填写后会请求 Runtime 的精确流年层；留空只生成原来的本命盘。"
    >
      <input
        id={`${productId}-target-year`}
        type="number"
        min="1800"
        max="2199"
        step="1"
        inputMode="numeric"
        {...register("targetYear")}
      />
    </Field>
  );
}

function TemporalTargetFields({
  errors,
  productId,
  register,
  supportsDay = false,
}: {
  errors: FieldErrors<TaskFormValues>;
  productId: "bazi" | "ziwei" | "qizheng";
  register: UseFormRegister<TaskFormValues>;
  supportsDay?: boolean;
}) {
  return (
    <>
      <TargetYearField errors={errors} productId={productId} register={register} />
      <div className={styles.twoColumns}>
        <Field htmlFor={`${productId}-target-month`} label="流月目标月份（可选）" error={errors.targetMonth?.message} help="填写后请求 Runtime 的精确月份层；与年份、日期互斥。">
          <input id={`${productId}-target-month`} type="month" {...register("targetMonth")} />
        </Field>
        {supportsDay ? (
          <Field htmlFor={`${productId}-target-date`} label="流日目标日期（可选）" error={errors.targetDate?.message} help="填写后请求 Runtime 的精确日期层；与年份、月份互斥。">
            <input id={`${productId}-target-date`} type="date" {...register("targetDate")} />
          </Field>
        ) : null}
      </div>
    </>
  );
}

const lineNames = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"] as const;

function SixLineProcess({
  errors,
  productId,
  register,
}: {
  errors: FieldErrors<TaskFormValues>["lines"];
  productId: string;
  register: UseFormRegister<TaskFormValues>;
}) {
  return (
    <fieldset className={styles.lineProcess}>
      <legend>六爻起卦作为第一步</legend>
      <p>按实际起卦顺序记录初爻到上爻；六次全部完成后才能继续，不会随机补数。</p>
      <div>
        {lineNames.map((line, index) => {
          const inputId = `${productId}-line-${index}`;
          const error = Array.isArray(errors) ? errors[index]?.message : undefined;
          return (
            <div className={styles.lineEntry} key={line}>
              <label htmlFor={inputId}>{line}</label>
              <select
                aria-describedby={error ? `${inputId}-error` : undefined}
                aria-invalid={Boolean(error)}
                autoComplete="off"
                id={inputId}
                required
                {...register(`lines.${index}` as const)}
              >
                <option value="">请选择</option>
                <option value="old-yin">老阴（6 · 动爻）</option>
                <option value="young-yang">少阳（7 · 静爻）</option>
                <option value="young-yin">少阴（8 · 静爻）</option>
                <option value="old-yang">老阳（9 · 动爻）</option>
              </select>
              {error ? <span className={styles.error} id={`${inputId}-error`} role="alert">{error}</span> : null}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
