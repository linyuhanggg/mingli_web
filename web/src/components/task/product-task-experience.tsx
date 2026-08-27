"use client";

import { Check, ChevronRight, Circle } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Status } from "@/components/ui/status";
import { ReadingResult } from "@/components/readings/reading-result";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import {
  confirmProfileDraft,
  createProfileDraft,
  discardProfileDraft,
  formatProfileOption,
  ApiError,
  listProfiles,
  type ProfileConfirmRequest,
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
  type MeihuaStartRequest,
  type PhysiognomyStartRequest,
  type PreviewStartRequest,
  type ProfileSummary,
  type TimeBasisPolicy,
  type SelectionStartRequest,
  type TaiyiStartRequest,
  type WenshiStartRequest,
} from "@/lib/api";
import { localDateTimeWithOffset } from "@/lib/date-time";
import { stableKeyForIntent, type IntentKey } from "@/lib/idempotency";
import {
  isProfileNameConflict,
  readProfileNameConflict,
  type ProfileNameConflict,
} from "@/lib/profile-conflict";
import {
  loadPendingStartTask,
  loginContinueHref,
  persistPendingStartTask,
  subscribePendingStartTasks,
} from "@/lib/login-continue";
import { mapStartReadingFailure, startReadingFailureAction } from "@/lib/start-reading-error";
import type { ProductDefinition } from "@/products/catalog";

import { ProfileNameConflictDialog } from "../profile-name-conflict-dialog";
import { ProfileRenameControl } from "../profile-rename-control";
import { ProductInputForm, type TaskFormValues } from "./product-input-form";
import {
  BaziDeepTaskFlow,
  baziPreviewRestoreHref,
  readBaziPreviewReadingId,
} from "./bazi-deep-task-flow";
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

function usesSavedProfiles(product: ProductDefinition): boolean {
  return product.group === "natal" || product.id === "hecan" || product.id === "canwen";
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

function InputTrustRail({ product }: { product: ProductDefinition }) {
  return (
    <aside className={styles.inputTrustRail} aria-label={`提交后的${product.name}盘面预览`}>
      <section className={styles.platePreview} aria-labelledby="task-plate-preview-title">
        <div className={styles.trustRailHeader}>
          <span>盘面骨架</span>
          <h2 id="task-plate-preview-title">提交后填入你的盘</h2>
          <p>以下干支只作示意骨架；真实盘面只使用提交后返回的版本化 ViewModel。</p>
        </div>
        <dl className={styles.plateSkeleton} aria-label="示意骨架，不是真实盘面">
          <div>
            <dt>年柱</dt>
            <dd>甲子</dd>
          </div>
          <div>
            <dt>月柱</dt>
            <dd>乙丑</dd>
          </div>
          <div>
            <dt>日柱</dt>
            <dd>丙寅</dd>
          </div>
          <div>
            <dt>时柱</dt>
            <dd>丁卯</dd>
          </div>
        </dl>
        <p className={styles.skeletonNote}>示意骨架：未知数据保持空态，不用默认干支冒充结果。</p>
      </section>
      <figure className={styles.citationSample}>
        <figcaption>已核对引文样张</figcaption>
        <blockquote>
          <p>「天道有寒暖，发育万物，人道得之，不可过也。」</p>
        </blockquote>
        <cite>《滴天髓》通神论 · verified_exact</cite>
      </figure>
      <section className={styles.trustSteps} aria-labelledby="task-trust-steps-title">
        <h2 id="task-trust-steps-title">三步看懂结果</h2>
        <ol>
          <li><strong>1. 提交资料</strong><span>只提交排盘必需字段。</span></li>
          <li><strong>2. 生成事实盘</strong><span>先展示可核对的盘面事实。</span></li>
          <li><strong>3. 核对引文</strong><span>解读句子绑定古籍证据。</span></li>
        </ol>
      </section>
    </aside>
  );
}

export function ProductTaskExperience({ product }: { product: ProductDefinition }) {
  const router = useRouter();
  const pathname = usePathname() || `/${product.id}`;
  const searchParams = useSearchParams();
  const requestedProfileVersionId = searchParams.get("profile") ?? "";
  const restoredBaziReadingId =
    product.id === "bazi" ? readBaziPreviewReadingId(searchParams) : null;
  const shouldLoadProfiles = usesSavedProfiles(product);
  const [stage, setStage] = useState<TaskStage>(restoredBaziReadingId ? "workbench" : "input");
  const [values, setValues] = useState<TaskFormValues | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitErrorState, setSubmitErrorState] = useState<"unavailable" | "error" | "unauthorized">("unavailable");
  const [submitErrorAction, setSubmitErrorAction] = useState<"login" | "retry" | null>(null);
  const [loginIntentKey, setLoginIntentKey] = useState<string | undefined>();
  const [nameConflict, setNameConflict] = useState<ProfileNameConflict | null>(null);
  const [createdProfile, setCreatedProfile] = useState<ProfileSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [baziPreviewReadingId, setBaziPreviewReadingId] = useState<string | null>(
    restoredBaziReadingId,
  );
  const [baziProfileVersionId, setBaziProfileVersionId] = useState<string | null>(
    restoredBaziReadingId ? requestedProfileVersionId || null : null,
  );
  const [ziweiPreviewReadingId, setZiweiPreviewReadingId] = useState<string | null>(null);
  const [liuyaoPreviewReadingId, setLiuyaoPreviewReadingId] = useState<string | null>(null);
  const [savedProfiles, setSavedProfiles] = useState<ProfileSummary[]>([]);
  const [savedProfilesLoading, setSavedProfilesLoading] = useState(
    shouldLoadProfiles,
  );
  const [savedProfilesError, setSavedProfilesError] = useState<string | null>(null);
  const [savedProfilesSignedOut, setSavedProfilesSignedOut] = useState(false);
  const [selectedProfileVersionId, setSelectedProfileVersionId] = useState("");
  const [savedProfilesAttempt, setSavedProfilesAttempt] = useState(0);
  const profileVersionRef = useRef<string | null>(null);
  const intentKeyRef = useRef<IntentKey | null>(null);
  const pendingProfileRef = useRef<{
    draftId: string;
    body: ProfileConfirmRequest;
    nextValues: TaskFormValues;
  } | null>(null);

  function writeBaziPreviewRoute(readingId: string | null, profileVersionId?: string | null) {
    if (typeof router.replace !== "function") return;
    router.replace(baziPreviewRestoreHref(pathname, searchParams, readingId, profileVersionId));
  }

  useEffect(() => {
    if (restoredBaziReadingId && requestedProfileVersionId) {
      profileVersionRef.current = requestedProfileVersionId;
    }
  }, [restoredBaziReadingId, requestedProfileVersionId]);

  useEffect(() => {
    if (!shouldLoadProfiles) return;

    let active = true;
    void listProfiles()
      .then(({ profiles }) => {
        if (!active) return;
        setSavedProfilesError(null);
        setSavedProfilesSignedOut(false);
        setSavedProfiles(profiles);
        setSelectedProfileVersionId((current) => {
          if (
            requestedProfileVersionId &&
            profiles.some(
              (profile) => profile.profile_version_id === requestedProfileVersionId,
            )
          ) {
            return requestedProfileVersionId;
          }
          if (
            current &&
            profiles.some((profile) => profile.profile_version_id === current)
          ) {
            return current;
          }
          return profiles[0]?.profile_version_id ?? "";
        });
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setSavedProfiles([]);
        setSelectedProfileVersionId("");
        if (reason instanceof ApiError && reason.status === 401) {
          setSavedProfilesSignedOut(true);
          setSavedProfilesError(null);
          return;
        }
        setSavedProfilesSignedOut(false);
        setSavedProfilesError(
          reason instanceof Error && reason.message
            ? reason.message
            : "读取已保存资料失败，请重试。",
        );
      })
      .finally(() => {
        if (active) setSavedProfilesLoading(false);
      });

    return () => {
      active = false;
    };
  }, [shouldLoadProfiles, requestedProfileVersionId, savedProfilesAttempt]);

  const resumeKey = searchParams.get("idempotency_key");
  const resumedTask = useSyncExternalStore(
    subscribePendingStartTasks,
    () => {
      const pending = loadPendingStartTask(resumeKey);
      return pending?.productId === product.id ? pending : null;
    },
    () => null,
  );

  async function startRuntimeReading(nextValues: TaskFormValues) {
    if (resumedTask && resumeKey) {
      intentKeyRef.current = { fingerprint: resumedTask.fingerprint, key: resumeKey };
    }
    if (!hasRuntimeStart(product)) {
      setStage("workbench");
      return;
    }
    if (busy) return;
    setBusy(true);
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);

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
        let profileVersionId = selectedProfileVersionId || profileVersionRef.current;
        if (!profileVersionId) {
          const draft = await createProfileDraft(nextValues.subject.trim() || undefined);
          const body: ProfileConfirmRequest = {
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
            on_name_conflict: "reject",
          };
          try {
            const profile = await confirmProfileDraft(draft.draft_id, body);
            profileVersionId = profile.profile_version_id;
            setCreatedProfile(profile);
          } catch (reason) {
            if (isProfileNameConflict(reason)) {
              pendingProfileRef.current = { draftId: draft.draft_id, body, nextValues };
              setNameConflict(readProfileNameConflict(reason));
              return;
            }
            throw reason;
          }
        }
        profileVersionRef.current = profileVersionId;
        if (product.id === "bazi") setBaziProfileVersionId(profileVersionId);

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
          writeBaziPreviewRoute(response.reading_version_id, profileVersionId);
        } else if (product.id === "ziwei") {
          setZiweiPreviewReadingId(response.reading_version_id);
          setStage("workbench");
        } else {
          router.push(`/app/readings/${response.reading_version_id}`);
        }
        return;
      }

      if (product.id === "hecan" || product.id === "canwen") {
        let profileVersionId = selectedProfileVersionId || profileVersionRef.current;
        if (!profileVersionId) {
          const draft = await createProfileDraft(nextValues.subject.trim() || undefined);
          const body: ProfileConfirmRequest = {
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
            on_name_conflict: "reject",
          };
          try {
            const profile = await confirmProfileDraft(draft.draft_id, body);
            profileVersionId = profile.profile_version_id;
            setCreatedProfile(profile);
          } catch (reason) {
            if (isProfileNameConflict(reason)) {
              pendingProfileRef.current = { draftId: draft.draft_id, body, nextValues };
              setNameConflict(readProfileNameConflict(reason));
              return;
            }
            throw reason;
          }
        }
        profileVersionRef.current = profileVersionId;
        const artByLabel: Record<string, "bazi" | "ziwei" | "qizheng"> = {
          八字: "bazi",
          紫微: "ziwei",
          七政: "qizheng",
        };
        const payload = {
          profile_version_id: profileVersionId,
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
        setLiuyaoPreviewReadingId(response.reading_version_id);
        setStage("workbench");
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
      const mapped = mapStartReadingFailure(reason);
      const action = startReadingFailureAction(reason);
      setSubmitErrorState(mapped.state);
      setSubmitError(mapped.title);
      setSubmitErrorAction(action);
      const intent = intentKeyRef.current;
      setLoginIntentKey(intent?.key);
      if (action === "login" && intent) {
        persistPendingStartTask(intent.key, {
          productId: product.id,
          fingerprint: intent.fingerprint,
          values: nextValues,
        });
      }
    } finally {
      setBusy(false);
    }
  }

  // 提交前摘要常驻在表单里（ProductInputForm 的 SubmitSummary），
  // 因此这里不再插入一个独立的「输入确认」页，直接进入生成。
  function handleConfirm(nextValues: TaskFormValues) {
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);
    setNameConflict(null);
    setValues(nextValues);
    void startRuntimeReading(nextValues);
  }

  async function cancelProfileConflict() {
    const pending = pendingProfileRef.current;
    pendingProfileRef.current = null;
    if (!pending) {
      setNameConflict(null);
      return;
    }
    setBusy(true);
    setSubmitError(null);
    try {
      await discardProfileDraft(pending.draftId);
      setNameConflict(null);
    } catch (reason) {
      pendingProfileRef.current = pending;
      const mapped = mapStartReadingFailure(reason);
      setSubmitErrorState(mapped.state);
      setSubmitError(mapped.title);
    } finally {
      setBusy(false);
    }
  }

  async function resolveProfileConflict(action: "overwrite" | "save_as") {
    const pending = pendingProfileRef.current;
    if (!pending) return;
    setBusy(true);
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);
    try {
      const profile = await confirmProfileDraft(pending.draftId, {
        ...pending.body,
        on_name_conflict: action,
      });
      pendingProfileRef.current = null;
      setNameConflict(null);
      setCreatedProfile(profile);
      profileVersionRef.current = profile.profile_version_id;
      setSelectedProfileVersionId(profile.profile_version_id);
      await startRuntimeReading(pending.nextValues);
    } catch (reason) {
      const mapped = mapStartReadingFailure(reason);
      setSubmitErrorState(mapped.state);
      setSubmitError(mapped.title);
      setSubmitErrorAction(startReadingFailureAction(reason));
      setLoginIntentKey(intentKeyRef.current?.key);
    } finally {
      setBusy(false);
    }
  }

  const shouldKeepZiweiInputMounted = product.id === "ziwei" && values !== null;
  const search = searchParams.toString();
  const loginHref = loginContinueHref(
    pathname,
    search ? `?${search}` : "",
    loginIntentKey ?? resumeKey ?? undefined,
  );

  return (
    <div className={styles.experience} data-product={product.id} data-stage={stage}>
      <ProfileNameConflictDialog
        conflict={nameConflict}
        busy={busy}
        onOverwrite={() => void resolveProfileConflict("overwrite")}
        onSaveAs={() => void resolveProfileConflict("save_as")}
        onCancel={() => {
          void cancelProfileConflict();
        }}
      />
      {stage !== "input" ? <TaskProgress product={product} stage={stage} /> : null}
      {createdProfile && stage === "workbench" ? (
        <div className={styles.renameBar}>
          <p>当前档案：{createdProfile.display_name?.trim() || formatProfileOption(createdProfile)}</p>
          <ProfileRenameControl profile={createdProfile} onRenamed={setCreatedProfile} />
        </div>
      ) : null}
      {stage === "input" || shouldKeepZiweiInputMounted ? (
        <div
          className={styles.inputLayout}
          data-input-region="first-screen"
          hidden={stage !== "input"}
        >
          <ProductInputForm
            key={resumedTask && resumeKey ? `resume-${resumeKey}` : "input"}
            busy={busy}
            onProfileVersionChange={(profileVersionId) => {
              setSelectedProfileVersionId(profileVersionId);
              profileVersionRef.current = profileVersionId || null;
              intentKeyRef.current = null;
            }}
            product={product}
            profileLookupError={savedProfilesError}
            profileLookupPending={savedProfilesLoading}
            profileLookupSignedOut={savedProfilesSignedOut}
            profiles={savedProfiles}
            selectedProfileVersionId={selectedProfileVersionId}
            initialValues={values ?? (resumedTask?.values as TaskFormValues | undefined)}
            onConfirm={handleConfirm}
            onPhotoChange={setPhotoFile}
            onRetryProfiles={() => {
              setSavedProfilesLoading(true);
              setSavedProfilesError(null);
              setSavedProfilesSignedOut(false);
              setSavedProfilesAttempt((value) => value + 1);
            }}
            submitError={submitError}
            submitErrorState={submitErrorState}
            submitErrorAction={submitErrorAction}
            loginHref={loginHref}
            hideUnknownHour={product.id === "bazi"}
            onRetry={() => {
              if (values) void startRuntimeReading(values);
            }}
          />
          <InputTrustRail product={product} />
        </div>
      ) : null}
      {stage === "workbench" && product.id !== "bazi" && product.id !== "ziwei" && product.id !== "liuyao" ? (
        <WorkbenchShell
          product={product}
          onBack={() => {
            profileVersionRef.current = null;
            setBaziProfileVersionId(null);
            intentKeyRef.current = null;
            setBaziPreviewReadingId(null);
            setZiweiPreviewReadingId(null);
            setSubmitError(null);
            setSubmitErrorAction(null);
            setLoginIntentKey(undefined);
            setStage("input");
          }}
        />
      ) : null}
      {stage === "workbench" && product.id === "liuyao" && !liuyaoPreviewReadingId ? (
        <Status
          actions={(
            <button
              type="button"
              onClick={() => {
                setSubmitError(null);
                setSubmitErrorAction(null);
                setLoginIntentKey(undefined);
                setStage("input");
              }}
            >
              返回录入
            </button>
          )}
          description="当前没有已确认的六爻任务句柄，不会伪造盘面。"
          state="empty"
          title="还没有可恢复的盘面"
        />
      ) : null}
      {stage === "workbench" && product.id === "liuyao" && liuyaoPreviewReadingId ? (
        <>
          <Status
            actions={(
              <button
                type="button"
                onClick={() => {
                  profileVersionRef.current = null;
                  intentKeyRef.current = null;
                  setLiuyaoPreviewReadingId(null);
                  setSubmitError(null);
                  setSubmitErrorAction(null);
                  setLoginIntentKey(undefined);
                  setStage("input");
                }}
              >
                返回录入
              </button>
            )}
            description="盘面留在本页。登录只用于保存、历史和深读。"
            state="success"
            title="六爻盘面"
          />
          <ReadingResult readingId={liuyaoPreviewReadingId} />
        </>
      ) : null}
      {stage === "workbench" && product.id === "bazi" && !baziPreviewReadingId ? (
        <Status
          actions={(
            <button
              type="button"
              onClick={() => {
                setSubmitError(null);
                setSubmitErrorAction(null);
                setLoginIntentKey(undefined);
                setStage("input");
                writeBaziPreviewRoute(null);
              }}
            >
              返回录入
            </button>
          )}
          description="当前没有已确认的八字任务句柄，不会伪造盘面。"
          state="empty"
          title="还没有可恢复的盘面"
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
            setSubmitErrorAction(null);
            setLoginIntentKey(undefined);
            setStage("input");
            writeBaziPreviewRoute(null);
          }}
          previewReadingId={baziPreviewReadingId}
          profileVersionId={baziProfileVersionId ?? ""}
          query={values?.issue.trim() || "请预览我的八字命盘。"}
        />
      ) : null}
      {stage === "workbench" && product.id === "ziwei" && !ziweiPreviewReadingId ? (
        <Status
          actions={
            <button
              type="button"
              onClick={() => {
                setSubmitError(null);
                setSubmitErrorAction(null);
                setLoginIntentKey(undefined);
                setStage("input");
              }}
            >
              返回录入
            </button>
          }
          description="当前没有已确认的紫微任务句柄，不会伪造盘面。"
          state="empty"
          title="还没有可恢复的盘面"
        />
      ) : null}
      {stage === "workbench" && product.id === "ziwei" && ziweiPreviewReadingId ? (
        <>
          <Status
            actions={
              <button
                type="button"
                onClick={() => {
                  profileVersionRef.current = null;
                  intentKeyRef.current = null;
                  setZiweiPreviewReadingId(null);
                  setSubmitError(null);
                  setSubmitErrorAction(null);
                  setLoginIntentKey(undefined);
                  setStage("input");
                }}
              >
                返回录入
              </button>
            }
            description="盘面留在本页。登录只用于保存、历史和深读。"
            state="empty"
            title="紫微盘面"
          />
          <ReadingResult readingId={ziweiPreviewReadingId} />
        </>
      ) : null}
    </div>
  );
}
