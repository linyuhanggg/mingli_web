"use client";

import { Check, ChevronRight, Circle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Status } from "@/components/ui/status";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import {
  confirmProfileDraft,
  createProfileDraft,
  getCapabilityProjection,
  startFengshuiReading,
  startPhysiognomyReading,
  startCanwenReading,
  startDaliurenReading,
  startHecanReading,
  startLiuyaoReading,
  startLumingNayinReading,
  startMeihuaReading,
  startPreviewReading,
  startQimenReading,
  startQizhengReading,
  startSelectionReading,
  startTaiyiReading,
  startWenshiReading,
  startZiweiReading,
  uploadPhysiognomyMedia,
  type EventArtStartRequest,
  type DaliurenStartRequest,
  type FengshuiStartRequest,
  type Gender,
  type HecanStartRequest,
  type LiuyaoStartRequest,
  type LumingNayinStartRequest,
  type CanwenStartRequest,
  type CapabilityProjection,
  type MeihuaStartRequest,
  type PhysiognomyStartRequest,
  type PreviewStartRequest,
  type TimeBasisPolicy,
  type SelectionStartRequest,
  type TaiyiStartRequest,
  type WenshiStartRequest,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";
import type { ProductDefinition } from "@/products/catalog";

import { ProductInputForm, type TaskFormValues } from "./product-input-form";
import { BaziDeepTaskFlow } from "./bazi-deep-task-flow";
import styles from "./task-shell.module.css";

type TaskStage = "input" | "workbench";

// 「输入确认」不再是独立一步：提交前摘要随填随现，长在录入面板底部。
const steps: Array<{ id: TaskStage | "report"; label: string }> = [
  { id: "input", label: "录入与核对" },
  { id: "workbench", label: "工作台" },
  { id: "report", label: "报告与追问" },
];

const stageIndex: Record<TaskStage, number> = { input: 0, workbench: 1 };

const RUNTIME_PRODUCT_IDS = new Set<ProductDefinition["id"]>([
  "bazi",
  "luming-nayin",
  "hecan",
  "canwen",
  "ziwei",
  "qizheng",
  "liuyao",
  "wenshi",
  "meihua",
  "qimen",
  "daliuren",
  "taiyi",
  "selection",
  "jianxiang",
  "fengshui",
]);

function hasRuntimeStart(product: ProductDefinition): boolean {
  return RUNTIME_PRODUCT_IDS.has(product.id);
}

function TaskProgress({ product, stage }: { product: ProductDefinition; stage: TaskStage }) {
  const current = stageIndex[stage];

  return (
    <nav className={styles.progress} aria-label={`${product.name}任务进度`}>
      <ol>
        {steps.map((step, index) => {
          const completed = index < current;
          const active = index === current;
          return (
            <li aria-current={active ? "step" : undefined} data-state={completed ? "complete" : active ? "active" : "pending"} key={step.id}>
              <span className={styles.stepIcon} aria-hidden="true">
                {completed ? <Check size={14} strokeWidth={2} /> : <Circle size={10} fill={active ? "currentColor" : "none"} />}
              </span>
              <span>{step.label}</span>
              {index < steps.length - 1 ? <ChevronRight className={styles.stepArrow} aria-hidden="true" size={15} /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function ModulePlan({
  product,
  capability,
}: {
  product: ProductDefinition;
  capability: CapabilityProjection | null;
}) {
  return (
    <aside className={styles.modulePlan} aria-labelledby={`${product.id}-module-plan`}>
      <div>
        <h2 id={`${product.id}-module-plan`}>{product.moduleTitle}</h2>
        <p>
          提交后按服务端实际返回的事实展示以下槽位；标注「待接入」的当前不会出现。
        </p>
      </div>
      <ol>
        {product.modules.map((module, index) => {
          const pending = product.pendingModules?.includes(module) ?? false;
          return (
            <li key={module} data-module-status={pending ? "pending" : "available"}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {module}
              {pending ? <em className={styles.modulePending}>待接入</em> : null}
            </li>
          );
        })}
      </ol>
      {capability?.tier === "B" ? (
        <div data-capability-tier="B">
          <Status
            state="success"
            title="确定性盘面与事实已开放"
            description="当前只提供服务端生成的盘面事实与边界，不提供断语或空白占位。"
          />
        </div>
      ) : capability?.tier === "C" ? (
        <div data-capability-tier="C">
          <Status state="unavailable" title="真实能力适配中" description={product.unavailableReason} />
        </div>
      ) : hasRuntimeStart(product) ? (
        <Status
          state="success"
          title="确定性盘面已接入"
          description="确认后由服务端生成盘面；深读、追问和导出仍按各术单独开放。"
        />
      ) : (
        <Status state="unavailable" title="真实能力适配中" description={product.unavailableReason} />
      )}
    </aside>
  );
}

export function ProductTaskExperience({ product }: { product: ProductDefinition }) {
  const router = useRouter();
  const [stage, setStage] = useState<TaskStage>("input");
  const [values, setValues] = useState<TaskFormValues | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [capability, setCapability] = useState<CapabilityProjection | null>(null);
  const [baziPreviewReadingId, setBaziPreviewReadingId] = useState<string | null>(null);
  const [baziProfileVersionId, setBaziProfileVersionId] = useState<string | null>(null);
  const profileVersionRef = useRef<string | null>(null);
  const intentKeyRef = useRef<IntentKey | null>(null);

  useEffect(() => {
    let active = true;
    void getCapabilityProjection()
      .then((response) => {
        if (!active) return;
        setCapability(
          response.capabilities.find((item) => item.capability_id === product.id) ?? null,
        );
      })
      .catch(() => {
        // The task surface remains usable when the read-only status endpoint is unavailable.
      });
    return () => {
      active = false;
    };
  }, [product.id]);

  async function startRuntimeReading(nextValues: TaskFormValues) {
    if (!hasRuntimeStart(product)) {
      setStage("workbench");
      return;
    }
    if (busy) return;
    setBusy(true);
    setSubmitError(null);

    try {
      if (product.id === "jianxiang") {
        if (!photoFile) {
          throw new Error("请重新选择见相照片后再提交。");
        }
        const media = await uploadPhysiognomyMedia(
          photoFile,
          nextValues.observationMode as "face" | "palm" | "posture" | "combined",
          nextValues.consent,
        );
        const payload: PhysiognomyStartRequest = {
          asset_id: media.asset_id,
          subject_ref: `sid-${media.asset_id.replaceAll("-", "")}`,
          ...(nextValues.observationNotes.trim() ? { query: nextValues.observationNotes.trim() } : {}),
          dimension_ids: ["state"],
          observations: [
            {
              region: nextValues.observationRegion,
              feature_kind: "visible_morphology",
              descriptor: nextValues.observationDescriptor,
              visibility: nextValues.observationVisibility as "full" | "partial",
              uncertainty: Number(nextValues.observationUncertainty),
            },
          ],
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startPhysiognomyReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      if (product.id === "fengshui") {
        const measurement = {
          measurement_id: "m-door",
          method: "user_compass",
          source_ref: "user-compass-1",
          source_type: "user_measurement",
          north_reference: "true",
          facing_degrees: Number(nextValues.fengshuiFacingDegrees),
          correction_degrees: 0,
          uncertainty_degrees: Number(nextValues.fengshuiUncertaintyDegrees),
          quality: "good",
        };
        const fengshuiSpec: FengshuiStartRequest["fengshui_spec"] = {
          schema_version: "mingli-fengshui-input-v1",
          property_scope: nextValues.fengshuiPropertyScope,
          subprofiles: ["liqi"],
          requested_form_variables: [],
          liqi: {
            selected_school: nextValues.fengshuiSelectedSchool,
            origin_basis: "door_trigram",
            origin_node_id: "door-1",
          },
          building: {},
          assets: [],
          observations: [],
          compass_measurements: [measurement],
          declared_orientation: {},
          layout_graph: {
            nodes: [{ node_id: "door-1", kind: "door", direction_measurement: measurement }],
            edges: [],
          },
        };
        const payload: FengshuiStartRequest = {
          fengshui_spec: fengshuiSpec,
          query: nextValues.observationNotes.trim() || "请展示已确认空间观察与风水结构事实。",
          dimension_ids: ["current_state", "direction"],
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startFengshuiReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      if (product.group === "natal") {
        let profileVersionId = profileVersionRef.current;
        if (!profileVersionId) {
          const draft = await createProfileDraft(nextValues.subject.trim());
          const profile = await confirmProfileDraft(draft.draft_id, {
            birth_datetime: localDateTimeWithOffset(
              `${nextValues.birthDate}T${nextValues.birthTime}`,
              nextValues.timezone,
            ),
            timezone: nextValues.timezone,
            location: nextValues.location.trim(),
            gender: nextValues.gender as Gender,
            time_basis_policy: (
              nextValues.timeStandard === "local-apparent-solar" ? "solar" : "civil"
            ) as TimeBasisPolicy,
            zi_hour_policy: "midnight",
            longitude: nextValues.longitude.trim() ? Number(nextValues.longitude) : undefined,
            latitude: nextValues.latitude.trim() ? Number(nextValues.latitude) : undefined,
            coordinate_source: nextValues.coordinateSource.trim() || undefined,
          });
          profileVersionId = profile.profile_version_id;
          profileVersionRef.current = profileVersionId;
          if (product.id === "bazi") setBaziProfileVersionId(profileVersionId);
        }

        const payload: PreviewStartRequest = {
          profile_version_id: profileVersionId,
          query: nextValues.issue.trim() || `请预览我的${product.name}命盘。`,
          dimension_ids: ["career"],
          ...(["bazi", "ziwei", "qizheng"].includes(product.id) && nextValues.targetYear.trim()
            ? { target_year: Number(nextValues.targetYear) }
            : {}),
          ...(["bazi", "ziwei", "qizheng"].includes(product.id) && nextValues.targetMonth.trim()
            ? { target_month: nextValues.targetMonth }
            : {}),
          ...(["bazi", "qizheng"].includes(product.id) && nextValues.targetDate.trim()
            ? { target_date: nextValues.targetDate }
            : {}),
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response =
          product.id === "bazi"
            ? await startPreviewReading(payload, intent.key)
            : product.id === "luming-nayin"
              ? await startLumingNayinReading(payload as LumingNayinStartRequest, intent.key)
            : product.id === "ziwei"
              ? await startZiweiReading(payload, intent.key)
              : await startQizhengReading(payload, intent.key);
        if (product.id === "bazi") {
          setBaziPreviewReadingId(response.reading_version_id);
          setStage("workbench");
        } else {
          router.push(`/app/readings/${response.reading_version_id}`);
        }
        return;
      }

      if (product.id === "hecan" || product.id === "canwen") {
        const artByLabel: Record<string, "bazi" | "ziwei" | "qizheng"> = {
          八字: "bazi",
          紫微: "ziwei",
          七政: "qizheng",
        };
        const payload = {
          profile_version_id: nextValues.profile.trim(),
          selected_art_ids: nextValues.arts
            .map((art) => artByLabel[art])
            .filter((art): art is "bazi" | "ziwei" | "qizheng" => Boolean(art)),
          ...(product.id === "canwen" ? { query: nextValues.issue.trim() } : {}),
          dimension_ids: ["career"] as const,
        } satisfies CanwenStartRequest | HecanStartRequest;
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response =
          product.id === "hecan"
            ? await startHecanReading(payload, intent.key)
            : await startCanwenReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      const eventDatetime = nextValues.eventTime
        ? localDateTimeWithOffset(nextValues.eventTime, nextValues.timezone)
        : "";
      const timeBasisPolicy =
        nextValues.timeStandard === "local-apparent-solar" ? "solar" : "civil";
      if (product.id === "taiyi") {
        const dimensionByFocus: Record<string, TaiyiStartRequest["dimension_ids"]> = {
          outcome: ["outcome"],
          timing: ["timing"],
          location: ["location"],
          state: ["state"],
        };
        const payload: TaiyiStartRequest = {
          event_datetime: eventDatetime,
          timezone: nextValues.timezone,
          location: nextValues.location.trim(),
          query: nextValues.issue.trim(),
          dimension_ids: dimensionByFocus[nextValues.focus] ?? ["outcome", "timing"],
          time_basis_policy: timeBasisPolicy,
          zi_hour_policy: "midnight",
          longitude: nextValues.longitude.trim() ? Number(nextValues.longitude) : undefined,
          latitude: nextValues.latitude.trim() ? Number(nextValues.latitude) : undefined,
          coordinate_source: nextValues.coordinateSource.trim() || undefined,
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startTaiyiReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      if (product.id === "selection") {
        const dimensionByFocus: Record<string, SelectionStartRequest["dimension_ids"]> = {
          timing: ["timing"],
          state: ["state"],
          location: ["location"],
        };
        const payload: SelectionStartRequest = {
          event_profile: nextValues.selectionEventProfile,
          requested_actions: nextValues.selectionActions
            .split(/[，,]/)
            .map((item) => item.trim())
            .filter(Boolean),
          date_range_start: nextValues.selectionStart,
          date_range_end: nextValues.selectionEnd,
          timezone: nextValues.timezone,
          location: nextValues.location.trim(),
          query: nextValues.issue.trim(),
          dimension_ids: dimensionByFocus[nextValues.focus] ?? ["timing", "state"],
          hard_constraints: nextValues.selectionConstraints.trim()
            ? { note: nextValues.selectionConstraints.trim() }
            : {},
          requested_scopes: [],
          include_folk_comparison: false,
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startSelectionReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      if (product.id === "liuyao") {
        const lineValues = nextValues.lines.map((line) => ({
          "old-yin": 6,
          "young-yang": 7,
          "young-yin": 8,
          "old-yang": 9,
        })[line]);
        const cast: LiuyaoStartRequest["cast"] =
          nextValues.focus === "coins"
            ? "digital_coin"
            : (lineValues as [number, number, number, number, number, number]);
        const payload: LiuyaoStartRequest = {
          cast,
          event_datetime: eventDatetime,
          timezone: nextValues.timezone,
          location: nextValues.location.trim(),
          query: nextValues.issue.trim(),
          dimension_ids: ["career"],
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startLiuyaoReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }

      if (product.id === "wenshi") {
        const lineValues = nextValues.lines.map((line) => ({
          "old-yin": 6,
          "young-yang": 7,
          "young-yin": 8,
          "old-yang": 9,
        })[line]);
        const payload: WenshiStartRequest = {
          cast: lineValues as [number, number, number, number, number, number],
          event_datetime: eventDatetime,
          timezone: nextValues.timezone,
          location: nextValues.location.trim(),
          query: nextValues.issue.trim(),
          dimension_ids: ["outcome", "timing"],
          time_basis_policy: timeBasisPolicy,
          zi_hour_policy: "midnight",
          longitude: nextValues.longitude.trim() ? Number(nextValues.longitude) : undefined,
          latitude: nextValues.latitude.trim() ? Number(nextValues.latitude) : undefined,
          coordinate_source: nextValues.coordinateSource.trim() || undefined,
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startWenshiReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }

      if (product.id === "meihua") {
        const dimensionByFocus: Record<string, MeihuaStartRequest["dimension_ids"]> = {
          outcome: ["outcome"],
          state: ["state"],
        };
        const castingMethod = nextValues.meihuaCastingMethod as NonNullable<MeihuaStartRequest["casting_method"]>;
        const source = {
          kind: castingMethod === "sound_count" || castingMethod === "observation" ? "user_observation" : "user_supplied",
          note: nextValues.meihuaSource.trim(),
        };
        const payload: MeihuaStartRequest = {
          casting_method: castingMethod,
          event_datetime: eventDatetime,
          timezone: nextValues.timezone,
          location: nextValues.location.trim(),
          query: nextValues.issue.trim(),
          dimension_ids: dimensionByFocus[nextValues.focus] ?? ["outcome", "state"],
          time_basis_policy: timeBasisPolicy,
          zi_hour_policy: "midnight",
          ...(castingMethod === "supplied_number"
            ? { number: Number(nextValues.meihuaNumber), provenance: source }
            : {}),
          ...(castingMethod === "sound_count"
            ? { count: Number(nextValues.meihuaCount), observation_source: source }
            : {}),
          ...(castingMethod === "observation"
            ? {
                upper_trigram: nextValues.meihuaUpperTrigram as MeihuaStartRequest["upper_trigram"],
                lower_trigram: nextValues.meihuaLowerTrigram as MeihuaStartRequest["lower_trigram"],
                observation_source: source,
              }
            : {}),
          ...(castingMethod === "supplied_hexagram"
            ? {
                upper_trigram: nextValues.meihuaUpperTrigram as MeihuaStartRequest["upper_trigram"],
                lower_trigram: nextValues.meihuaLowerTrigram as MeihuaStartRequest["lower_trigram"],
                moving_line: Number(nextValues.meihuaMovingLine),
                provenance: source,
              }
            : {}),
        };
        const intent = stableKeyForIntent(intentKeyRef.current, {
          product: product.id,
          payload,
        });
        intentKeyRef.current = intent;
        const response = await startMeihuaReading(payload, intent.key);
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }

      const dimensionByFocus: Record<string, EventArtStartRequest["dimension_ids"]> =
        product.id === "qimen"
          ? {
              action: ["outcome"],
              situation: ["state"],
              timing: ["timing"],
            }
          : {
              progress: ["outcome"],
              people: ["relationship"],
              outcome: ["outcome"],
              timing: ["timing"],
            };
      const payload: EventArtStartRequest = {
        event_datetime: eventDatetime,
        timezone: nextValues.timezone,
        location: nextValues.location.trim(),
        query: nextValues.issue.trim(),
        dimension_ids: dimensionByFocus[nextValues.focus] ?? ["outcome", "timing"],
        time_basis_policy: timeBasisPolicy,
        zi_hour_policy: "midnight",
      };
      const daliurenPayload: DaliurenStartRequest = {
        ...payload,
        ...(nextValues.focus === "timing"
          ? {
              timing_start: nextValues.timingStart,
              timing_end: nextValues.timingEnd,
            }
          : {}),
      };
      const intent = stableKeyForIntent(intentKeyRef.current, {
        product: product.id,
        payload: product.id === "qimen" ? payload : daliurenPayload,
      });
      intentKeyRef.current = intent;
      const response =
        product.id === "qimen"
          ? await startQimenReading(payload, intent.key)
          : await startDaliurenReading(daliurenPayload, intent.key);
      router.push(`/app/readings/${response.reading_version_id}`);
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : "盘面启动失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  // 提交前摘要常驻在表单里（ProductInputForm 的 SubmitSummary），
  // 因此这里不再插入一个独立的「输入确认」页，直接进入生成。
  function handleConfirm(nextValues: TaskFormValues) {
    setSubmitError(null);
    setValues(nextValues);
    void startRuntimeReading(nextValues);
  }

  return (
    <div className={styles.experience} data-product={product.id}>
      <TaskProgress product={product} stage={stage} />
      {stage === "input" ? (
        <div className={styles.inputLayout}>
          <ProductInputForm
            busy={busy}
            product={product}
            initialValues={values ?? undefined}
            onConfirm={handleConfirm}
            onPhotoChange={setPhotoFile}
            submitError={submitError}
          />
          <ModulePlan product={product} capability={capability} />
        </div>
      ) : null}
      {stage === "workbench" && product.id !== "bazi" ? (
        <WorkbenchShell
          product={product}
          onBack={() => {
            profileVersionRef.current = null;
            setBaziProfileVersionId(null);
            intentKeyRef.current = null;
            setBaziPreviewReadingId(null);
            setSubmitError(null);
            setStage("input");
          }}
        />
      ) : null}
      {stage === "workbench" && product.id === "bazi" && baziPreviewReadingId ? (
        <BaziDeepTaskFlow
          onBack={() => {
            profileVersionRef.current = null;
            setBaziProfileVersionId(null);
            intentKeyRef.current = null;
            setBaziPreviewReadingId(null);
            setSubmitError(null);
            setStage("input");
          }}
          previewReadingId={baziPreviewReadingId}
          profileVersionId={baziProfileVersionId ?? ""}
          query={values?.issue.trim() || "请预览我的八字命盘。"}
        />
      ) : null}
    </div>
  );
}
