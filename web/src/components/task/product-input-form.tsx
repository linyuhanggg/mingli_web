"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Camera, Info, Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { useForm, useWatch, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { z } from "zod";

import { Status } from "@/components/ui/status";
import { IanaTimeZoneOptions } from "@/components/iana-timezone-options";
import { formatProfileOption, type ProfileSummary } from "@/lib/api";
import {
  CHINA_TIME_ZONE,
  joinLocation,
  loadDivisions,
  type ProvinceCityAreas,
} from "@/lib/china-division";
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
  timingStart: z.string(),
  timingEnd: z.string(),
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
  // 不给默认值：分段控件“两个都没选中”是可见状态，而下拉停在“暂不指定”
  // 看起来像已经答过，用户直到提交才知道它非法。
  gender: "",
  timeStandard: "civil",
  longitude: "",
  latitude: "",
  coordinateSource: "",
  issue: "",
  focus: "",
  eventTime: "",
  timingStart: "",
  timingEnd: "",
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
  timingStart: { id: "timing-start", label: "应期观察开始" },
  timingEnd: { id: "timing-end", label: "应期观察结束" },
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

function productFieldLabel(productId: string, fieldName: string, fallback: string) {
  if (productId === "fengshui" && fieldName === "location") return "空间所在地点";
  if (productId === "liuyao" || productId === "meihua") {
    if (fieldName === "location") return "事件地点";
    if (fieldName === "timezone") return "事件时区";
  }
  if (productId === "liuyao" && fieldName === "focus") return "起卦方式";
  return fallback;
}

function taskErrorField(productId: string, fieldName: string, errors?: FieldErrors<TaskFormValues>) {
  const field = taskErrorFields[fieldName];
  if (!field) return null;
  if (fieldName === "lines") {
    return { ...field, id: `${productId}-line-${firstLineErrorIndex(errors?.lines)}` };
  }
  return {
    ...field,
    id: `${productId}-${field.id}`,
    label: productFieldLabel(productId, fieldName, field.label),
  };
}

function schemaFor(product: ProductDefinition, usesSavedProfile = false) {
  return taskSchemaBase.superRefine((values, context) => {
    if (product.group === "natal") {
      if (!usesSavedProfile && values.subject.trim().length > 80) context.addIssue({ code: "custom", path: ["subject"], message: "名称最多 80 个字" });
      if (!usesSavedProfile && !/^\d{4}-\d{2}-\d{2}$/.test(values.birthDate)) context.addIssue({ code: "custom", path: ["birthDate"], message: "请选择完整出生日期" });
      if (!usesSavedProfile && !values.unknownTime && !values.birthTime) context.addIssue({ code: "custom", path: ["birthTime"], message: "请选择出生时间" });
      if (!usesSavedProfile && !values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写出生地点" });

      if (["bazi", "luming-nayin", "ziwei", "qizheng"].includes(product.id)) {
        if (!usesSavedProfile && values.calendar !== "gregorian") {
          context.addIssue({ code: "custom", path: ["calendar"], message: "请填写公历出生日期。" });
        }
        if (!usesSavedProfile && values.unknownTime) {
          context.addIssue({ code: "custom", path: ["birthTime"], message: "请填写明确的出生时间。" });
        }
        if (!usesSavedProfile && values.gender !== "male" && values.gender !== "female") {
          context.addIssue({ code: "custom", path: ["gender"], message: "请选择性别后再建立盘面档案" });
        }
        if (!usesSavedProfile && !values.timezone.trim()) {
          context.addIssue({ code: "custom", path: ["timezone"], message: "请选择出生时区" });
        } else if (!usesSavedProfile && !isIanaTimeZone(values.timezone)) {
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

      if (product.id === "qizheng" && !usesSavedProfile) {
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
      if (product.group === "event" && !values.focus) {
        context.addIssue({
          code: "custom",
          path: ["focus"],
          message: product.id === "liuyao" ? "请选择起卦方式" : "请选择场景或侧重",
        });
      }
      if (product.id !== "selection" && !values.eventTime) context.addIssue({ code: "custom", path: ["eventTime"], message: "请选择事件时空" });

      if (["liuyao", "meihua", "qimen", "daliuren", "wenshi", "taiyi", "selection"].includes(product.id)) {
        if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写事件地点" });
        if (!values.timezone.trim()) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择事件时区" });
        else if (!isIanaTimeZone(values.timezone)) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择有效的 IANA 事件时区" });
      }

      if (product.id === "daliuren" && values.focus === "timing") {
        if (!values.timingStart) {
          context.addIssue({ code: "custom", path: ["timingStart"], message: "请选择应期观察开始日期" });
        }
        if (!values.timingEnd) {
          context.addIssue({ code: "custom", path: ["timingEnd"], message: "请选择应期观察结束日期" });
        }
        if (values.timingStart && values.timingEnd) {
          if (values.timingEnd < values.timingStart) {
            context.addIssue({ code: "custom", path: ["timingEnd"], message: "应期观察结束日期不能早于开始日期" });
          } else {
            const start = new Date(`${values.timingStart}T00:00:00Z`);
            const end = new Date(`${values.timingEnd}T00:00:00Z`);
            if (end.getTime() - start.getTime() > 30 * 24 * 60 * 60 * 1000) {
              context.addIssue({ code: "custom", path: ["timingEnd"], message: "应期观察范围最多包含 31 天" });
            }
          }
        }
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
      if (!usesSavedProfile) {
        if (values.subject.trim().length > 80) context.addIssue({ code: "custom", path: ["subject"], message: "名称最多 80 个字" });
        if (values.calendar !== "gregorian") context.addIssue({ code: "custom", path: ["calendar"], message: "请填写公历出生日期。" });
        if (!/^\d{4}-\d{2}-\d{2}$/.test(values.birthDate)) context.addIssue({ code: "custom", path: ["birthDate"], message: "请选择完整出生日期" });
        if (!values.birthTime) context.addIssue({ code: "custom", path: ["birthTime"], message: "请选择出生时间" });
        if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写出生地点" });
        if (values.gender !== "male" && values.gender !== "female") context.addIssue({ code: "custom", path: ["gender"], message: "请选择性别后再建立立命档案" });
        if (!isIanaTimeZone(values.timezone)) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择有效的 IANA 出生时区" });
      }
      if (values.arts.length < 2) context.addIssue({ code: "custom", path: ["arts"], message: "至少选择两术" });
      if (!values.arts.includes("八字")) context.addIssue({ code: "custom", path: ["arts"], message: "请以八字为主理，至少再选择一术" });
    }

    if (product.id === "canwen") {
      if (!values.issue.trim()) context.addIssue({ code: "custom", path: ["issue"], message: "请写清当前问题" });
      if (!usesSavedProfile) {
        if (values.subject.trim().length > 80) context.addIssue({ code: "custom", path: ["subject"], message: "名称最多 80 个字" });
        if (values.calendar !== "gregorian") context.addIssue({ code: "custom", path: ["calendar"], message: "请填写公历出生日期。" });
        if (!/^\d{4}-\d{2}-\d{2}$/.test(values.birthDate)) context.addIssue({ code: "custom", path: ["birthDate"], message: "请选择完整出生日期" });
        if (!values.birthTime) context.addIssue({ code: "custom", path: ["birthTime"], message: "请选择出生时间" });
        if (!values.location.trim()) context.addIssue({ code: "custom", path: ["location"], message: "请填写出生地点" });
        if (values.gender !== "male" && values.gender !== "female") context.addIssue({ code: "custom", path: ["gender"], message: "请选择性别后再建立立命档案" });
        if (!isIanaTimeZone(values.timezone)) context.addIssue({ code: "custom", path: ["timezone"], message: "请选择有效的 IANA 出生时区" });
      }
      if (values.arts.length < 2) context.addIssue({ code: "custom", path: ["arts"], message: "至少选择两术" });
      if (!values.arts.includes("八字")) context.addIssue({ code: "custom", path: ["arts"], message: "请以八字为主理，至少再选择一术" });
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

type JianxiangCaptureState = "empty" | "selected" | "deleted";

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

const OBSERVATION_REGION_LABELS: Record<string, string> = {
  forehead: "额头",
  left_eyebrow: "左眉",
  right_eyebrow: "右眉",
  left_eye: "左眼",
  right_eye: "右眼",
  nose: "鼻部",
  mouth: "口唇",
  chin: "下巴",
  jawline: "下颌线",
  left_ear: "左耳",
  right_ear: "右耳",
  left_cheek: "左脸颊",
  right_cheek: "右脸颊",
  complexion: "面部肤色",
  left_palm: "左掌",
  right_palm: "右掌",
  life_line: "生命线",
  head_line: "智慧线",
  heart_line: "感情线",
  fate_line: "事业线",
  head_posture: "头部姿态",
  shoulder_line: "肩线",
  spine_curve: "脊柱曲线",
  walking_gait: "行走姿态",
  sitting_posture: "坐姿",
};

const OBSERVATION_DESCRIPTOR_LABELS: Record<string, string> = {
  region_visible: "部位可见",
  relative_width_broad: "相对较宽",
  relative_width_narrow: "相对较窄",
  contour_rounded: "轮廓圆润",
  contour_flat: "轮廓平缓",
  line_straight: "线形较直",
  line_curved: "线形弯曲",
  density_even: "密度均匀",
  density_sparse_visible: "可见密度偏疏",
  aperture_open: "开合较大",
  aperture_narrow: "开合较窄",
  alignment_level: "基本平齐",
  bridge_straight: "鼻梁较直",
  tip_rounded: "鼻头圆润",
  lip_line_straight: "唇线较直",
  lip_line_curved: "唇线弯曲",
  mouth_closed: "嘴唇闭合",
  mouth_open: "嘴唇张开",
  contour_square: "轮廓方正",
  contour_pointed: "轮廓偏尖",
  outline_rounded: "外缘圆润",
  outline_angular: "外缘有棱角",
  outline_visible: "外缘可见",
  partially_visible: "部分可见",
  contour_full_relative: "相对饱满",
  contour_flat_relative: "相对平缓",
  ridge_visible: "掌纹可见",
  texture_even_visible: "可见纹理均匀",
  line_continuous: "线条连续",
  line_discontinuous: "线条不连续",
  line_deep_visible: "可见线条较深",
  line_shallow_visible: "可见线条较浅",
  level: "水平",
  forward_tilt: "前倾",
  backward_tilt: "后仰",
  uneven: "不平齐",
  aligned: "基本挺直",
  curved: "有弯曲",
  steady: "稳定",
  upright: "直立",
  forward_lean: "前倾",
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

/** 二选一的分段控件：比下拉少一次点击，且两个选项同时可见。 */
function SegmentedField({
  legend,
  name,
  value,
  options,
  required,
  error,
  help,
  onChange,
}: {
  legend: string;
  name: string;
  value: string;
  options: ReadonlyArray<{ value: string; label: string; disabled?: boolean }>;
  required?: boolean;
  error?: string;
  help?: string;
  onChange: (next: string) => void;
}) {
  return (
    <fieldset className={styles.field} id={name} tabIndex={-1}>
      <legend>
        {legend}
        {required ? <span className={styles.requiredMark}>必填</span> : null}
      </legend>
      <div className={styles.segmented} role="group">
        {options.map((option) => (
          <label
            className={styles.segment}
            data-selected={value === option.value ? "true" : "false"}
            key={option.value}
          >
            <input
              checked={value === option.value}
              disabled={option.disabled}
              name={name}
              onChange={() => onChange(option.value)}
              type="radio"
              value={option.value}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
      {help ? <p>{help}</p> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </fieldset>
  );
}

const YEAR_MAX = new Date().getFullYear();
const YEARS = Array.from({ length: YEAR_MAX - 1900 + 1 }, (_, index) => YEAR_MAX - index);
const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1);
const HOURS = Array.from({ length: 24 }, (_, index) => index);
const MINUTES = Array.from({ length: 60 }, (_, index) => index);

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function daysInMonth(year: string, month: string) {
  const y = Number(year);
  const m = Number(month);
  if (!y || !m) return 31;
  return new Date(y, m, 0).getDate();
}

/** 年 / 月 / 日 三列选择，比原生 date 控件少一次弹层，也不受浏览器差异影响。 */
function BirthDateParts({
  id,
  value,
  error,
  onChange,
}: {
  id: string;
  value: string;
  error?: string;
  onChange: (next: string) => void;
}) {
  const [year = "", month = "", day = ""] = value.split("-");
  const max = daysInMonth(year, month);
  const commit = (nextYear: string, nextMonth: string, nextDay: string) => {
    const clamped = nextDay ? Math.min(Number(nextDay), daysInMonth(nextYear, nextMonth)) : "";
    onChange(`${nextYear}-${nextMonth}-${clamped === "" ? "" : pad(clamped)}`);
  };

  return (
    <fieldset className={styles.field} id={id} tabIndex={-1}>
      <legend>
        出生日期<span className={styles.requiredMark}>必填</span>
      </legend>
      <div className={styles.dateParts}>
        <select
          aria-label="出生年份"
          onChange={(event) => commit(event.target.value, month, day)}
          value={year}
        >
          <option value="">年</option>
          {YEARS.map((item) => (
            <option key={item} value={String(item)}>{item}</option>
          ))}
        </select>
        <select
          aria-label="出生月份"
          onChange={(event) => commit(year, event.target.value, day)}
          value={month}
        >
          <option value="">月</option>
          {MONTHS.map((item) => (
            <option key={item} value={pad(item)}>{item}</option>
          ))}
        </select>
        <select
          aria-label="出生日期"
          onChange={(event) => commit(year, month, event.target.value)}
          value={day}
        >
          <option value="">日</option>
          {Array.from({ length: max }, (_, index) => index + 1).map((item) => (
            <option key={item} value={pad(item)}>{item}</option>
          ))}
        </select>
      </div>
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </fieldset>
  );
}

const SHICHEN = [
  "子", "丑", "丑", "寅", "寅", "卯", "卯", "辰", "辰", "巳", "巳", "午",
  "午", "未", "未", "申", "申", "酉", "酉", "戌", "戌", "亥", "亥", "子",
] as const;

/**
 * 只把用户选的民用钟表时间标注成对应时段，方便核对是否填错上午/下午。
 * 真太阳时换算、早晚子时与换日规则仍然只由服务端 Runtime 判定。
 */
function shichenLabel(hour: number) {
  const name = SHICHEN[hour];
  if (name === "子") {
    return { name, range: "23:00–01:00", note: "夜子/早子的归属由服务端按规则确定" };
  }
  const start = (Math.floor((hour + 1) / 2) * 2 - 1 + 24) % 24;
  return { name, range: `${pad(start)}:00–${pad((start + 2) % 24)}:00`, note: "" };
}

/**
 * 省 / 市 / 区县三级联动。选中国内地点时时区自动推导为 Asia/Shanghai，
 * 不再让用户单独填一次 IANA 时区；海外或查不到时切换成直接输入。
 */
function BirthPlaceParts({
  id,
  value,
  error,
  onChange,
  onTimeZone,
}: {
  id: string;
  value: string;
  error?: string;
  onChange: (next: string) => void;
  onTimeZone: (zone: string) => void;
}) {
  const [divisions, setDivisions] = useState<ProvinceCityAreas | null>(null);
  const [manual, setManual] = useState(false);
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");

  useEffect(() => {
    if (manual) return;
    let cancelled = false;
    void loadDivisions().then((data) => {
      if (!cancelled) setDivisions(data);
    });
    return () => {
      cancelled = true;
    };
  }, [manual]);

  const cities = province && divisions ? Object.keys(divisions[province] ?? {}) : [];
  const areas = province && city && divisions ? (divisions[province]?.[city] ?? []) : [];

  const commit = (nextProvince: string, nextCity: string, nextArea: string) => {
    onChange(joinLocation(nextProvince, nextCity, nextArea));
    if (nextProvince) onTimeZone(CHINA_TIME_ZONE);
  };

  return (
    <fieldset className={styles.field} id={id} tabIndex={-1}>
      <legend>
        出生地点<span className={styles.requiredMark}>必填</span>
      </legend>
      {manual ? (
        <>
          <input
            aria-label="出生地点"
            onChange={(event) => onChange(event.target.value)}
            placeholder="例如 Tokyo, Japan"
            value={value}
          />
          <button className={styles.placeSwitch} onClick={() => setManual(false)} type="button">
            回到省 / 市 / 区县选择
          </button>
        </>
      ) : (
        <>
          <div className={styles.placeParts}>
            <select
              aria-label="出生省份"
              onChange={(event) => {
                setProvince(event.target.value);
                setCity("");
                commit(event.target.value, "", "");
              }}
              value={province}
            >
              <option value="">省 / 直辖市</option>
              {divisions
                ? Object.keys(divisions).map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))
                : null}
            </select>
            <select
              aria-label="出生城市"
              disabled={!province}
              onChange={(event) => {
                setCity(event.target.value);
                commit(province, event.target.value, "");
              }}
              value={city}
            >
              <option value="">城市</option>
              {cities.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <select
              aria-label="出生区县"
              disabled={!city}
              onChange={(event) => commit(province, city, event.target.value)}
              value={value.split(" / ")[2] ?? ""}
            >
              <option value="">区 / 县</option>
              {areas.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>
          <button className={styles.placeSwitch} onClick={() => setManual(true)} type="button">
            海外或找不到？直接输入
          </button>
        </>
      )}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </fieldset>
  );
}

function BirthTimeParts({
  id,
  value,
  disabled,
  error,
  onChange,
}: {
  id: string;
  value: string;
  disabled?: boolean;
  error?: string;
  onChange: (next: string) => void;
}) {
  const [hour = "", minute = ""] = value.split(":");
  const commit = (nextHour: string, nextMinute: string) => {
    if (!nextHour) {
      onChange("");
      return;
    }
    onChange(`${nextHour}:${nextMinute || "00"}`);
  };
  const readout = hour === "" ? null : shichenLabel(Number(hour));

  return (
    <fieldset className={styles.field} disabled={disabled} id={id} tabIndex={-1}>
      <legend>
        出生时间<span className={styles.requiredMark}>必填</span>
      </legend>
      <div className={styles.timeParts}>
        <select
          aria-label="出生小时"
          onChange={(event) => commit(event.target.value, minute)}
          value={hour}
        >
          <option value="">时</option>
          {HOURS.map((item) => (
            <option key={item} value={pad(item)}>{pad(item)}</option>
          ))}
        </select>
        <select
          aria-label="出生分钟"
          onChange={(event) => commit(hour, event.target.value)}
          value={minute}
        >
          <option value="">分</option>
          {MINUTES.map((item) => (
            <option key={item} value={pad(item)}>{pad(item)}</option>
          ))}
        </select>
      </div>
      {readout ? (
        <p className={styles.timeReadout}>
          民用钟表 <strong>{hour}:{minute || "00"}</strong> 属 <strong>{readout.name}时</strong>
          <span>（{readout.range}{readout.note ? `；${readout.note}` : ""}）</span>
        </p>
      ) : null}
      {disabled ? <p>已标记时辰未知，不需要填写具体时间。</p> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
    </fieldset>
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
  profiles = [],
  selectedProfileVersionId = "",
  onProfileVersionChange,
  profileLookupPending = false,
  profileLookupError = null,
  profileLookupSignedOut = false,
  onRetryProfiles,
  busy = false,
  submitError = null,
  submitErrorState = "unavailable",
  submitErrorAction = null,
  loginHref = "/auth/login",
  onRetry,
  hideUnknownHour = false,
}: {
  product: ProductDefinition;
  initialValues?: TaskFormValues;
  onConfirm: (values: TaskFormValues) => void;
  onPhotoChange?: (file: File | null) => void;
  profiles?: readonly ProfileSummary[];
  selectedProfileVersionId?: string;
  onProfileVersionChange?: (profileVersionId: string) => void;
  profileLookupPending?: boolean;
  profileLookupError?: string | null;
  profileLookupSignedOut?: boolean;
  onRetryProfiles?: () => void;
  busy?: boolean;
  submitError?: string | null;
  submitErrorState?: "unavailable" | "error" | "unauthorized";
  submitErrorAction?: "login" | "retry" | null;
  loginHref?: string;
  onRetry?: () => void;
  hideUnknownHour?: boolean;
}) {
  const schema = useMemo(
    () => schemaFor(product, Boolean(selectedProfileVersionId)),
    [product, selectedProfileVersionId],
  );
  const {
    clearErrors,
    control,
    formState: { errors },
    handleSubmit,
    register,
    setValue,
  } = useForm<TaskFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ...(initialValues ?? defaultValues), unknownTime: false },
    mode: "onSubmit",
    shouldFocusError: false,
  });
  const unknownTime = useWatch({ control, name: "unknownTime" });
  const calendar = useWatch({ control, name: "calendar" });
  const gender = useWatch({ control, name: "gender" });
  const birthDate = useWatch({ control, name: "birthDate" });
  const birthTime = useWatch({ control, name: "birthTime" });
  const timeStandard = useWatch({ control, name: "timeStandard" });
  const location = useWatch({ control, name: "location" });
  const summaryValues = useWatch({ control }) as TaskFormValues;
  const focus = useWatch({ control, name: "focus" });
  const meihuaCastingMethod = useWatch({ control, name: "meihuaCastingMethod" });
  const observationMode = useWatch({ control, name: "observationMode" });
  const observationRegion = useWatch({ control, name: "observationRegion" });
  const observationOptions = OBSERVATION_OPTIONS[observationMode] ?? FACE_DESCRIPTOR_OPTIONS;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [captureState, setCaptureState] = useState<JianxiangCaptureState>("empty");
  const [photoName, setPhotoName] = useState("");
  const selectedProfile = profiles.find(
    (profile) => profile.profile_version_id === selectedProfileVersionId,
  );
  useEffect(() => {
    if (!selectedProfileVersionId) return;
    clearErrors([
      "subject",
      "calendar",
      "birthDate",
      "birthTime",
      "location",
      "timezone",
      "gender",
      "longitude",
      "latitude",
      "coordinateSource",
    ]);
  }, [clearErrors, selectedProfileVersionId]);
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

  const isCompactBaziInput = product.id === "bazi";
  const usesCrossProfile = product.id === "hecan" || product.id === "canwen";
  const showUnknownHour = !hideUnknownHour && ["bazi", "ziwei", "qizheng", "luming-nayin"].includes(product.id);

  return (
    <form
      aria-label={`${product.name}任务输入`}
      className={styles.formPanel}
      data-compact-natal={isCompactBaziInput ? "true" : undefined}
      noValidate
      onSubmit={handleSubmit((values) => onConfirm({ ...values, unknownTime: false }), handleInvalid)}
    >
      {!isCompactBaziInput ? (
        <div className={styles.formHeader}>
          <div>
            <h2>{product.name}任务输入</h2>
            <p>只填写本任务需要的资料。带“必填”的项目会在本机先检查。</p>
          </div>
          <span><Info aria-hidden="true" size={16} /> {confirmHint(product.id)}</span>
        </div>
      ) : null}

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

      {product.group === "natal" && (profiles.length > 0 || profileLookupError) ? (
        <fieldset className={styles.fieldGroup}>
          <legend>排盘资料</legend>
          {profileLookupError ? (
            <>
              <Status
                state="unavailable"
                title="暂时无法读取已保存资料"
                description="可以重试读取，也可以继续填写新资料。"
              />
              {onRetryProfiles ? (
                <button
                  className={styles.secondaryButton}
                  onClick={onRetryProfiles}
                  type="button"
                >
                  重新读取已保存资料
                </button>
              ) : null}
            </>
          ) : null}
          {!profileLookupPending && profiles.length > 0 ? (
            <Field
              help="默认选择最近确认的档案；只有资料发生变化时才需要重新录入。"
              htmlFor={`${product.id}-saved-profile`}
              label="排盘资料"
            >
              <select
                id={`${product.id}-saved-profile`}
                onChange={(event) => onProfileVersionChange?.(event.currentTarget.value)}
                value={selectedProfileVersionId}
              >
                {profiles.map((profile) => (
                  <option key={profile.profile_version_id} value={profile.profile_version_id}>
                    {formatProfileOption(profile)}
                  </option>
                ))}
                <option value="">重新录入并建立新档案</option>
              </select>
            </Field>
          ) : null}
          {selectedProfile ? (
            <p className={styles.productNote}>
              本次将直接使用已保存的不可变档案版本；如出生资料有变化，请选择重新录入。
            </p>
          ) : !profileLookupPending ? (
            <p className={styles.productNote}>
              本次将核对出生资料并建立新的不可变档案版本。
            </p>
          ) : null}
        </fieldset>
      ) : null}

      {usesCrossProfile ? (
        <fieldset className={styles.fieldGroup}>
          <legend>立命资料</legend>
          <p className={styles.productNote}>合参前需要一份已确认的立命档案。</p>
          {profileLookupPending ? (
            <Status
              state="loading"
              title="正在读取已确认档案…"
              description="读取完成后可直接选择档案，页面不会要求填写内部编号。"
            />
          ) : null}
          {profileLookupError ? (
            <>
              <Status
                state="unavailable"
                title="暂时无法读取已保存资料"
                description="可以重试，也可以填写出生资料建立新档案。"
              />
              {onRetryProfiles ? (
                <button className={styles.secondaryButton} onClick={onRetryProfiles} type="button">
                  重新读取已保存资料
                </button>
              ) : null}
            </>
          ) : null}
          {!profileLookupPending && profiles.length > 0 ? (
            <Field
              help="选择一份已确认的立命档案。出生资料以服务端确认版本为准，不会用称呼或占位文字代替。"
              htmlFor={`${product.id}-saved-profile`}
              label="立命资料"
            >
              <select
                aria-describedby={`${product.id}-saved-profile-help`}
                id={`${product.id}-saved-profile`}
                onChange={(event) => onProfileVersionChange?.(event.currentTarget.value)}
                value={selectedProfileVersionId}
              >
                {profiles.map((profile) => (
                  <option key={profile.profile_version_id} value={profile.profile_version_id}>
                    {formatProfileOption(profile)}
                  </option>
                ))}
                <option value="">重新录入并建立新档案</option>
              </select>
            </Field>
          ) : null}
          {selectedProfile ? (
            <p className={styles.productNote}>
              本次将使用已确认的立命档案：{formatProfileOption(selectedProfile)}。
            </p>
          ) : !profileLookupPending ? (
            <>
              {profileLookupSignedOut ? (
                <p className={styles.productNote}>
                  <Link href={`/auth/login?returnTo=/${product.id}`}>登录后选择已有档案</Link>
                  ，或直接填写出生资料建立新档案。
                </p>
              ) : null}
              <p className={styles.productNote}>填写后会在服务端确认一份不可变档案，再用来合参。</p>
            </>
          ) : null}
        </fieldset>
      ) : null}

      {(product.group === "natal" || usesCrossProfile) && !selectedProfileVersionId && !profileLookupPending ? (
        <fieldset className={styles.fieldGroup}>
          <legend>{usesCrossProfile ? "出生资料（建立新档案）" : "出生资料"}</legend>
          <Field
            htmlFor={`${product.id}-subject`}
            label="受测对象"
            error={errors.subject?.message}
            help={isCompactBaziInput ? undefined : "可以填写便于识别的称呼；留空则由服务端生成回退名。"}
          >
            <input
              id={`${product.id}-subject`}
              aria-describedby={
                errors.subject
                  ? `${product.id}-subject-error`
                  : isCompactBaziInput
                    ? undefined
                    : `${product.id}-subject-help`
              }
              autoComplete="name"
              {...register("subject")}
            />
          </Field>
          <div className={isCompactBaziInput ? undefined : styles.twoColumns}>
            {!isCompactBaziInput ? (
              <SegmentedField
                error={errors.calendar?.message}
                help={
                  product.id === "luming-nayin"
                    ? "请填写公历出生日期。"
                    : undefined
                }
                legend="历法"
                name={`${product.id}-calendar`}
                onChange={(next) => setValue("calendar", next, { shouldDirty: true })}
                options={[
                  { value: "gregorian", label: "公历" },
                  {
                    value: "lunar",
                    label: "农历",
                    disabled: ["bazi", "luming-nayin", "ziwei", "qizheng"].includes(product.id),
                  },
                ]}
                value={calendar}
              />
            ) : null}
            <SegmentedField
              error={errors.gender?.message}
              legend="性别"
              name={`${product.id}-gender`}
              onChange={(next) => setValue("gender", next, { shouldDirty: true })}
              options={[
                { value: "male", label: "男" },
                { value: "female", label: "女" },
              ]}
              required
              value={gender}
            />
          </div>
          {/* 年/月/日 + 时/分 并成一行，和青囊的「诞辰之候」一样一眼填完。 */}
          <div className={styles.dateTimeRow}>
            <BirthDateParts
              error={errors.birthDate?.message}
              id={`${product.id}-birth-date`}
              onChange={(next) => setValue("birthDate", next, { shouldDirty: true })}
              value={birthDate}
            />
            <BirthTimeParts
              disabled={unknownTime}
              error={errors.birthTime?.message}
              id={`${product.id}-birth-time`}
              onChange={(next) => setValue("birthTime", next, { shouldDirty: true })}
              value={birthTime}
            />
          </div>
          {showUnknownHour ? (
            <div className={styles.unknownHour}>
              <label>
                <input checked={false} disabled type="checkbox" />
                不知道出生时辰
              </label>
              <p>请填写明确的出生时间。</p>
              {isCompactBaziInput ? <p>确认后生成盘面</p> : null}
            </div>
          ) : null}
          {product.id !== "qizheng" ? (
            <BirthPlaceParts
              error={errors.location?.message}
              id={`${product.id}-location`}
              onChange={(next) => setValue("location", next, { shouldDirty: true })}
              onTimeZone={(zone) => setValue("timezone", zone, { shouldDirty: true })}
              value={location}
            />
          ) : (
            <fieldset className={styles.fieldGroup}>
              <legend>出生地点与坐标</legend>
              <p className={styles.productNote}>七政专有：地点将用于经纬度与时区校准，并保留坐标来源。</p>
              <BirthPlaceParts
                error={errors.location?.message}
                id={`${product.id}-location`}
                onChange={(next) => setValue("location", next, { shouldDirty: true })}
                onTimeZone={(zone) => setValue("timezone", zone, { shouldDirty: true })}
                value={location}
              />
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
            </fieldset>
          )}

          <SegmentedField
            legend="时间口径"
            name={`${product.id}-time-standard`}
            onChange={(next) => setValue("timeStandard", next, { shouldDirty: true })}
            options={[
              { value: "civil", label: "民用钟表时间" },
              { value: "local-apparent-solar", label: "当地视太阳时" },
            ]}
            value={timeStandard}
          />

          <details className={styles.advanced}>
            <summary>高级排盘选项</summary>
            <div className={styles.advancedBody}>
              <Field htmlFor={`${product.id}-timezone`} label="出生时区" error={errors.timezone?.message} help="选中国内地点后自动填好；海外地点请自行确认。">
                <input id={`${product.id}-timezone`} aria-describedby={errors.timezone ? `${product.id}-timezone-error` : `${product.id}-timezone-help`} autoComplete="off" list={`${product.id}-timezone-options`} placeholder="例如 Asia/Shanghai" {...register("timezone")} />
                <IanaTimeZoneOptions id={`${product.id}-timezone-options`} />
              </Field>
              <ProductSpecificNatalOptions errors={errors} product={product} register={register} />
            </div>
          </details>
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
                {product.id === "daliuren" ? <><option value="progress">事情进展</option><option value="people">人事关系</option><option value="outcome">结果观察</option><option value="timing">应期观察</option></> : null}
                {product.id === "taiyi"
                  ? TAIYI_FOCUS_OPTIONS.map(([value, optionLabel]) => (
                      <option key={value} value={value}>{optionLabel}</option>
                    ))
                  : null}
                {product.id === "selection"
                  ? SELECTION_FOCUS_OPTIONS.map(([value, optionLabel]) => (
                      <option key={value} value={value}>{optionLabel}</option>
                    ))
                  : null}
              </select>
            </Field>
          ) : null}
          {product.id !== "selection" ? (
            <Field htmlFor={`${product.id}-event-time`} label={product.id === "wenshi" ? "同一事件时空" : product.id === "taiyi" ? "参考时间" : "事件时间"} error={errors.eventTime?.message} help="默认使用你明确选择的当地时间，不读取设备位置。">
              <input id={`${product.id}-event-time`} type="datetime-local" aria-describedby={errors.eventTime ? `${product.id}-event-time-error` : `${product.id}-event-time-help`} {...register("eventTime")} />
            </Field>
          ) : null}
          {product.id === "daliuren" && focus === "timing" ? (
            <div className={styles.twoColumns}>
              <Field htmlFor="daliuren-timing-start" label="应期观察开始" error={errors.timingStart?.message} help="用于激活大六壬已核验的候选日期规则。">
                <input id="daliuren-timing-start" type="date" {...register("timingStart")} />
              </Field>
              <Field htmlFor="daliuren-timing-end" label="应期观察结束" error={errors.timingEnd?.message} help="范围最多 31 天；候选日期不是现实保证。">
                <input id="daliuren-timing-end" type="date" {...register("timingEnd")} />
              </Field>
            </div>
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
                  <option value="observation">观物起卦</option>
                  <option value="supplied_hexagram">已知卦象起卦</option>
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
                  <Field htmlFor="meihua-source" label={meihuaCastingMethod === "observation" ? "观物来源" : "卦象资料来源"} error={errors.meihuaSource?.message}>
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
            <p>原图不会被排盘服务读取；请只提交你已经核对、且能说明可见程度的观察，不让系统从照片自动猜测。</p>
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
                  {Object.keys(observationOptions).map((region) => (
                    <option key={region} value={region}>
                      {OBSERVATION_REGION_LABELS[region] ?? "未公开观察部位"}
                    </option>
                  ))}
                </select>
              </Field>
              <Field htmlFor="jianxiang-observation-descriptor" label="观察描述" error={errors.observationDescriptor?.message}>
                <select id="jianxiang-observation-descriptor" {...register("observationDescriptor")}>
                  {(observationOptions[observationRegion] ?? ["region_visible"]).map((descriptor) => (
                    <option key={descriptor} value={descriptor}>
                      {OBSERVATION_DESCRIPTOR_LABELS[descriptor] ?? "未公开观察描述"}
                    </option>
                  ))}
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
            <p id="jianxiang-file-help">确认后文件才会上传到本次私有会话，并按页面显示的期限自动过期。</p>
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
                <button className={styles.secondaryButton} onClick={clearPhoto} type="button">删除本地照片</button>
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
          <ChoiceGroup id={`${product.id}-arts`} legend={product.id === "hecan" ? "至少选择两术（八字为主理，至少再选一术）" : "选择命盘"} help={product.id === "hecan" ? "八字为主理，再从紫微、七政中选择。没有结果就说没有可展示的互证。" : "八字为主理，再选择需要参证的命盘。没有结果就说没有可展示的互证。"} error={errors.arts?.message}>
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

      {!isCompactBaziInput ? (
        <SubmitSummary
          product={product}
          profileLabel={selectedProfile ? formatProfileOption(selectedProfile) : null}
          values={summaryValues}
        />
      ) : null}

      {submitError ? (
        submitErrorAction ? (
          <Status
            actions={
              submitErrorAction === "login" ? (
                <Link href={loginHref}>登录后继续</Link>
              ) : (
                <button type="button" onClick={() => onRetry?.()}>
                  重试
                </button>
              )
            }
            state={submitErrorState}
            title={submitError}
          />
        ) : submitErrorState === "error" ? (
          <p className={styles.error} role="alert">{submitError}</p>
        ) : (
          <Status
            state={submitErrorState === "unauthorized" ? "unauthorized" : "unavailable"}
            title={submitError}
          />
        )
      ) : null}

      <button
        aria-busy={busy}
        className={styles.primaryButton}
        disabled={busy}
        type="submit"
      >
        {busy ? "正在生成盘面…" : submitLabel(product)}
      </button>
      <details className={styles.submitBoundary}>
        <summary>提交后会发生什么</summary>
        <p>
          {RUNTIME_SUBMIT_IDS.includes(product.id)
            ? "资料提交到对应的服务端排盘服务并跳转到私有结果页；盘面在服务端确定性生成，不在浏览器计算。深读、追问和导出仍按各术单独开放。"
            : "检查只发生在当前页面。继续后会在工作台明确显示未接入能力，不扣权益。"}
        </p>
      </details>
    </form>
  );
}

const RUNTIME_SUBMIT_IDS = [
  "bazi", "luming-nayin", "ziwei", "qizheng", "hecan", "canwen", "liuyao",
  "meihua", "qimen", "daliuren", "taiyi", "selection", "fengshui", "wenshi",
];

const SUBMIT_LABELS: Record<string, string> = {
  bazi: "立即排盘（免费）· 查看八字四柱",
  ziwei: "立即排盘（免费）· 查看十二宫",
  qizheng: "立即排盘（免费）· 查看星盘",
  "luming-nayin": "立即排盘（免费）· 查看禄命纳音",
  liuyao: "立即起卦 · 查看本卦与变卦",
  meihua: "立即起卦 · 查看本卦与体用",
  qimen: "立即起局 · 查看九宫",
  daliuren: "立即起课 · 查看四课三传",
  taiyi: "立即起局 · 查看年度结构",
  selection: "立即排候选 · 查看日期排序",
  wenshi: "立即起卦 · 三术分别呈现",
  hecan: "立即合参 · 各术分别呈现",
  canwen: "立即合参 · 各术分别呈现",
  jianxiang: "开始观照 · 生成结构化观察",
  fengshui: "立即起盘 · 查看形势与理气",
};

function submitLabel(product: ProductDefinition) {
  return SUBMIT_LABELS[product.id] ?? `立即排盘 · 查看${product.moduleTitle}`;
}

function confirmHint(productId: string) {
  if (productId === "hecan" || productId === "canwen") {
    return "确认后生成";
  }
  if (RUNTIME_SUBMIT_IDS.includes(productId) || productId === "jianxiang") {
    return "确认后生成盘面";
  }
  return "确认后生成";
}

const VALUE_LABELS: Record<string, string> = {
  gregorian: "公历", lunar: "农历",
  male: "男", female: "女",
  civil: "民用钟表时间", "local-apparent-solar": "当地视太阳时",
  coins: "三枚硬币", manual: "手动记录",
  outcome: "结果观察", state: "状态变化", action: "行动选择",
  situation: "局势判断", timing: "时机观察", progress: "事情进展",
  people: "人事关系", location: "空间范围",
  face: "面相", palm: "手相", posture: "体态", combined: "综合观照",
};

const TAIYI_FOCUS_OPTIONS = [
  ["outcome", "年度结果"],
  ["timing", "时间节律"],
  ["location", "空间范围"],
  ["state", "结构状态"],
] as const;

const SELECTION_FOCUS_OPTIONS = [
  ["timing", "时间排序"],
  ["state", "候选状态"],
  ["location", "方位条件"],
] as const;

function label(value: string) {
  return VALUE_LABELS[value] ?? value;
}

function focusLabel(productId: string, value: string) {
  const productOptions = productId === "taiyi"
    ? TAIYI_FOCUS_OPTIONS
    : productId === "selection"
      ? SELECTION_FOCUS_OPTIONS
      : null;
  if (productOptions) {
    return productOptions.find(([optionValue]) => optionValue === value)?.[1] ?? value;
  }
  return label(value);
}

/**
 * 提交前摘要常驻在表单底部，随填随更新——METIS 的「输入确认」也是这样长在同一页上，
 * 而不是把用户推到一个独立步骤。
 */
function SubmitSummary({
  product,
  profileLabel,
  values,
}: {
  product: ProductDefinition;
  profileLabel: string | null;
  values: TaskFormValues;
}) {
  // 历法、时区、时间口径都有默认值；用户一个字都没填时不该先冒出一张摘要。
  const started = Boolean(
    profileLabel ||
    values.subject.trim() ||
      values.birthDate ||
      values.issue.trim() ||
      values.observationNotes.trim() ||
      values.photoSelected,
  );
  if (!started) return null;

  const rows: Array<readonly [string, string]> = [];

  const usesCrossProfile = product.id === "hecan" || product.id === "canwen";

  if (usesCrossProfile && profileLabel) {
    rows.push(["立命资料", profileLabel]);
    if (values.issue.trim()) rows.push(["问题", values.issue]);
  } else if (usesCrossProfile) {
    rows.push([
      "立命资料",
      values.subject.trim() && values.birthDate
        ? `新建档案（${values.subject.trim()} · ${values.birthDate}）`
        : "",
    ]);
    if (values.issue.trim()) rows.push(["问题", values.issue]);
  } else if (product.group === "natal" && profileLabel) {
    rows.push(["排盘资料", profileLabel]);
  } else if (product.group === "natal") {
    rows.push(["受测对象", values.subject]);
    rows.push(["历法", label(values.calendar)]);
    rows.push(["性别", values.gender ? label(values.gender) : ""]);
    rows.push(["出生日期", values.birthDate]);
    rows.push([
      "出生时间",
      values.unknownTime
        ? "时辰未知"
        : values.birthTime
          ? `${values.birthTime}（${shichenLabel(Number(values.birthTime.split(":")[0])).name}时）`
          : "",
    ]);
    rows.push(["出生地点", values.location]);
    rows.push(["出生时区", values.timezone]);
    rows.push(["时间口径", label(values.timeStandard)]);
  } else {
    rows.push(["受测对象", values.subject]);
    rows.push(["问题", values.issue]);
    if (values.focus) rows.push(["侧重", focusLabel(product.id, values.focus)]);
    if (product.id === "daliuren" && values.focus === "timing") {
      rows.push(["应期观察开始", values.timingStart]);
      rows.push(["应期观察结束", values.timingEnd]);
    }
    if (product.id === "jianxiang") {
      rows.push(["观照模式", label(values.observationMode)]);
      rows.push(["用户补充信息", values.observationNotes]);
      rows.push(["保存范围", values.saveToArchive ? "见相档案（需服务端确认）" : "仅本次任务"]);
    }
    rows.push(["事件时间", values.eventTime]);
    rows.push(["事件地点", values.location]);
    rows.push(["事件时区", values.timezone]);
  }

  const filled = rows.filter(([, value]) => Boolean(value));
  if (filled.length === 0) return null;

  return (
    <section aria-label="提交前摘要" className={styles.submitSummary}>
      <h3>即将提交</h3>
      <dl>
        {filled.map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
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
      <p className={styles.productNote}>八字专有：后续可分别确认真太阳时换算、早晚子时与换日规则。</p>
      <fieldset className={styles.fieldGroup}>
        <legend>目标时间层（可选，三选一）</legend>
        <p className={styles.productNote}>不填时由系统按当前免费规则返回可用流年；填写一项后计算对应的流年、流月或流日。</p>
        <div className={styles.twoColumns}>
          <Field htmlFor="bazi-target-year" label="流年目标年份" error={errors.targetYear?.message}>
            <input id="bazi-target-year" inputMode="numeric" placeholder="例如 2026" {...register("targetYear")} />
          </Field>
          <Field htmlFor="bazi-target-month" label="流月目标月份" error={errors.targetMonth?.message}>
            <input id="bazi-target-month" type="month" {...register("targetMonth")} />
          </Field>
        </div>
        <Field htmlFor="bazi-target-date" label="流日目标日期" error={errors.targetDate?.message}>
          <input id="bazi-target-date" type="date" {...register("targetDate")} />
        </Field>
      </fieldset>
    </>
  );
  if (product.id === "ziwei") return null;
  if (product.id === "qizheng") return null;
  return null;
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
