"use client";

import { Check, ChevronRight, Circle } from "lucide-react";
import { AnimatePresence } from "motion/react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Status } from "@/components/ui/status";
import { ReadingResult } from "@/components/readings/reading-result";
import {
  ChartReadyReveal,
  ChartStructureSkeleton,
} from "@/components/readings/chart-structure-skeleton";
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
  clearRecoverableReading,
  inlineReadingRestoreHref,
  loadRecoverableReading,
  readInlineReadingId,
  resolveReadingStartedAt,
  saveRecoverableReading,
  type RecoverableReading,
} from "@/lib/reading-recovery";
import {
  consumePendingStartTask,
  isPendingStartStorageFailure,
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

const PENDING_START_READ_ERROR = "无法恢复登录前的排盘资料";
const PENDING_START_WRITE_ERROR = "无法保存登录续接资料，请允许本网站使用会话存储后重试。";
const CHART_SKELETON_DELAY_MS = 300;
const CHART_RETURN_DELAY_MS = 15_000;
const CHART_START_TIMEOUT_MS = 60_000;

type PendingStartFormState = {
  version: 1;
  formValues: TaskFormValues;
  profileVersionId?: string;
};

function readPendingStartFormState(values: unknown): PendingStartFormState | null {
  if (!values || typeof values !== "object" || Array.isArray(values)) return null;
  const candidate = values as Record<string, unknown>;
  if (
    candidate.version === 1
    && candidate.formValues
    && typeof candidate.formValues === "object"
    && !Array.isArray(candidate.formValues)
  ) {
    const profileVersionId =
      typeof candidate.profileVersionId === "string"
        ? candidate.profileVersionId.trim()
        : "";
    return {
      version: 1,
      formValues: candidate.formValues as TaskFormValues,
      ...(profileVersionId ? { profileVersionId } : {}),
    };
  }
  return {
    version: 1,
    formValues: values as TaskFormValues,
  };
}

function profileInputFingerprint(body: ProfileConfirmRequest): string {
  const { on_name_conflict: conflictAction, ...profileInput } = body;
  void conflictAction;
  return JSON.stringify(profileInput);
}

const BAZI_PREVIEW_RECOVERY_PREFIX = "mingli.bazi-preview-recovery:";

export type BaziPreviewRecoveryState = {
  version: 1;
  readingId: string;
  profileVersionId: string;
  question: string;
};

function baziPreviewRecoveryKey(readingId: string): string {
  return `${BAZI_PREVIEW_RECOVERY_PREFIX}${readingId}`;
}

export function persistBaziPreviewRecoveryState(
  recovery: Omit<BaziPreviewRecoveryState, "version">,
): BaziPreviewRecoveryState | null {
  const readingId = recovery.readingId.trim();
  const profileVersionId = recovery.profileVersionId.trim();
  const question = recovery.question.trim();
  if (!readingId || !profileVersionId || !question) return null;
  const persisted: BaziPreviewRecoveryState = {
    version: 1,
    readingId,
    profileVersionId,
    question,
  };
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(
        baziPreviewRecoveryKey(readingId),
        JSON.stringify(persisted),
      );
    } catch {
      // A blocked storage write must not break the free chart. A later refresh
      // will fail closed instead of inventing a deep-reading question.
    }
  }
  return persisted;
}

export function readBaziPreviewRecoveryState(
  readingId: string | null | undefined,
): BaziPreviewRecoveryState | null {
  const expectedReadingId = readingId?.trim() ?? "";
  if (!expectedReadingId || typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(baziPreviewRecoveryKey(expectedReadingId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<BaziPreviewRecoveryState>;
    const profileVersionId = parsed.profileVersionId?.trim() ?? "";
    const question = parsed.question?.trim() ?? "";
    if (
      parsed.version !== 1
      || parsed.readingId?.trim() !== expectedReadingId
      || !profileVersionId
      || !question
    ) {
      return null;
    }
    return {
      version: 1,
      readingId: expectedReadingId,
      profileVersionId,
      question,
    };
  } catch {
    return null;
  }
}

function clearBaziPreviewRecoveryState(readingId: string | null | undefined): void {
  const normalizedReadingId = readingId?.trim() ?? "";
  if (!normalizedReadingId || typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(baziPreviewRecoveryKey(normalizedReadingId));
  } catch {
    // The route is still cleared even when browser storage is unavailable.
  }
}

function subscribeBrowserReady(): () => void {
  return () => undefined;
}

function browserReadySnapshot(): boolean {
  return true;
}

function serverReadySnapshot(): boolean {
  return false;
}

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
  const s3Art =
    product.id === "liuyao" || product.id === "meihua" || product.id === "daliuren";
  const previewTitle =
    product.id === "liuyao"
      ? "六爻自上而下核对"
      : product.id === "meihua"
        ? "本卦、互卦、变卦依次展开"
        : product.id === "daliuren"
          ? "天地盘与四课三传分区呈现"
          : "提交后填入你的盘";
  const previewCopy = s3Art
    ? "这里只预告结果结构；真实盘面只使用提交后返回的版本化 ViewModel。"
    : "以下干支只作示意骨架；真实盘面只使用提交后返回的版本化 ViewModel。";

  return (
    <aside className={styles.inputTrustRail} aria-label={`提交后的${product.name}盘面预览`}>
      <section className={styles.platePreview} aria-labelledby="task-plate-preview-title">
        <div className={styles.trustRailHeader}>
          <span>盘面骨架</span>
          <h2 id="task-plate-preview-title">{previewTitle}</h2>
          <p>{previewCopy}</p>
        </div>
        {product.id === "liuyao" ? (
          <ol className={styles.liuyaoSkeleton} aria-label="六爻结果结构示意">
            {[6, 5, 4, 3, 2, 1].map((line) => (
              <li key={line}>
                <span>{line === 6 ? "上爻" : line === 1 ? "初爻" : `${line}爻`}</span>
                <i aria-hidden="true" />
                <small>等待服务端爻值</small>
              </li>
            ))}
          </ol>
        ) : product.id === "meihua" ? (
          <ol className={styles.meihuaSkeleton} aria-label="梅花本互变结果结构示意">
            {["本卦", "互卦", "变卦"].map((label) => (
              <li key={label}>
                <strong>{label}</strong>
                <span>等待服务端卦象</span>
              </li>
            ))}
          </ol>
        ) : product.id === "daliuren" ? (
          <div className={styles.daliurenSkeleton} aria-label="大六壬课传结果结构示意">
            <ol aria-label="四课">
              {["一课", "二课", "三课", "四课"].map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ol>
            <ol aria-label="三传">
              {["初传", "中传", "末传"].map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ol>
          </div>
        ) : (
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
        )}
        <p className={styles.skeletonNote}>
          {s3Art
            ? "结构预览：未知事实保持空态，不用示例卦、爻或课传冒充结果。"
            : "示意骨架：未知数据保持空态，不用默认干支冒充结果。"}
        </p>
      </section>
      {s3Art ? (
        <section className={styles.sourceBoundary} aria-labelledby="task-source-boundary-title">
          <h2 id="task-source-boundary-title">事实与依据同盘回看</h2>
          <p>有精确依据时才显示原文与定位；没有证据的字段保持缺口，不展示内部数据或推测。</p>
        </section>
      ) : (
        <figure className={styles.citationSample}>
          <figcaption>已核对引文样张</figcaption>
          <blockquote>
            <p>「天道有寒暖，发育万物，人道得之，不可过也。」</p>
          </blockquote>
          <cite>《滴天髓》通神论 · verified_exact</cite>
        </figure>
      )}
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
  const resumeKey = searchParams.get("idempotency_key");
  const [, setResumeReadAttempt] = useState(0);
  const pendingStartSnapshot = useSyncExternalStore(
    subscribePendingStartTasks,
    () => {
      const pending = loadPendingStartTask(resumeKey);
      if (isPendingStartStorageFailure(pending)) return pending;
      return pending?.productId === product.id ? pending : null;
    },
    () => null,
  );
  const resumeStorageFailure = isPendingStartStorageFailure(pendingStartSnapshot)
    ? pendingStartSnapshot
    : null;
  const resumedTask = isPendingStartStorageFailure(pendingStartSnapshot)
    ? null
    : pendingStartSnapshot;
  const resumedFormState = readPendingStartFormState(resumedTask?.values);
  const resumedProfileVersionId = resumedFormState?.profileVersionId ?? "";
  const resumedSelectionContext =
    resumedTask && resumeKey ? `${resumeKey}:${resumedTask.fingerprint}` : "";
  const requestedProfileVersionId = searchParams.get("profile") ?? "";
  const restoredBaziReadingId =
    product.id === "bazi" ? readBaziPreviewReadingId(searchParams) : null;
  const restoredInlineReadingId = readInlineReadingId(product.id, searchParams);
  const shouldLoadProfiles = usesSavedProfiles(product);
  const [stage, setStage] = useState<TaskStage>(
    restoredBaziReadingId || restoredInlineReadingId ? "workbench" : "input",
  );
  const [values, setValues] = useState<TaskFormValues | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitErrorState, setSubmitErrorState] = useState<"unavailable" | "error" | "unauthorized">("unavailable");
  const [submitErrorAction, setSubmitErrorAction] = useState<"login" | "retry" | null>(null);
  const [loginIntentKey, setLoginIntentKey] = useState<string | undefined>();
  const [nameConflict, setNameConflict] = useState<ProfileNameConflict | null>(null);
  const [createdProfile, setCreatedProfile] = useState<ProfileSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [chartWaitAttempt, setChartWaitAttempt] = useState<number | null>(null);
  const [showChartSkeleton, setShowChartSkeleton] = useState(false);
  const [focusChartReadyReveal, setFocusChartReadyReveal] = useState(false);
  const [canReturnFromChartWait, setCanReturnFromChartWait] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [baziPreviewReadingId, setBaziPreviewReadingId] = useState<string | null>(
    restoredBaziReadingId,
  );
  const [baziPreviewRecovery, setBaziPreviewRecovery] =
    useState<BaziPreviewRecoveryState | null>(null);
  const browserReady = useSyncExternalStore(
    subscribeBrowserReady,
    browserReadySnapshot,
    serverReadySnapshot,
  );
  const restoredBaziRecovery = browserReady
    ? readBaziPreviewRecoveryState(restoredBaziReadingId)
    : null;
  const activeBaziRecovery =
    baziPreviewRecovery?.readingId === baziPreviewReadingId
      ? baziPreviewRecovery
      : restoredBaziRecovery?.readingId === baziPreviewReadingId
        ? restoredBaziRecovery
        : null;
  const [inlineRecovery, setInlineRecovery] = useState<RecoverableReading | null>(null);
  const [inlineRestarting, setInlineRestarting] = useState(false);
  const [ziweiPreviewReadingId, setZiweiPreviewReadingId] = useState<string | null>(
    product.id === "ziwei" ? restoredInlineReadingId : null,
  );
  const [liuyaoPreviewReadingId, setLiuyaoPreviewReadingId] = useState<string | null>(
    product.id === "liuyao" ? restoredInlineReadingId : null,
  );
  const activeInlineReadingId = product.id === "ziwei"
    ? ziweiPreviewReadingId
    : product.id === "liuyao"
      ? liuyaoPreviewReadingId
      : null;
  const restoredInlineRecovery = browserReady && activeInlineReadingId
    ? loadRecoverableReading(product.id, activeInlineReadingId)
    : null;
  const activeInlineRecovery =
    inlineRecovery?.productId === product.id
      && inlineRecovery.readingVersionId === activeInlineReadingId
      ? inlineRecovery
      : restoredInlineRecovery;
  const [savedProfiles, setSavedProfiles] = useState<ProfileSummary[]>([]);
  const [savedProfilesLoading, setSavedProfilesLoading] = useState(
    shouldLoadProfiles,
  );
  const [savedProfilesError, setSavedProfilesError] = useState<string | null>(null);
  const [savedProfilesSignedOut, setSavedProfilesSignedOut] = useState(false);
  const [selectedProfileVersionId, setSelectedProfileVersionId] = useState("");
  const [savedProfilesAttempt, setSavedProfilesAttempt] = useState(0);
  const profileVersionRef = useRef<string | null>(null);
  const confirmedProfileInputRef = useRef<string | null>(null);
  const profileSelectionContextRef = useRef<string | null>(null);
  const intentKeyRef = useRef<IntentKey | null>(null);
  const pendingProfileRef = useRef<{
    draftId: string;
    body: ProfileConfirmRequest;
    nextValues: TaskFormValues;
  } | null>(null);
  const chartWaitAttemptRef = useRef(0);

  useEffect(() => {
    if (chartWaitAttempt === null) return;

    const skeletonTimer = window.setTimeout(
      () => setShowChartSkeleton(true),
      CHART_SKELETON_DELAY_MS,
    );
    const returnTimer = window.setTimeout(
      () => setCanReturnFromChartWait(true),
      CHART_RETURN_DELAY_MS,
    );
    const timeoutTimer = window.setTimeout(() => {
      if (chartWaitAttemptRef.current !== chartWaitAttempt) return;
      chartWaitAttemptRef.current += 1;
      setShowChartSkeleton(false);
      setCanReturnFromChartWait(false);
      setChartWaitAttempt(null);
      setBusy(false);
      setSubmitErrorState("error");
      setSubmitError("排盘等待超过 60 秒，已停止当前页面等待；原资料仍可直接重试。");
      setSubmitErrorAction("retry");
    }, CHART_START_TIMEOUT_MS);

    return () => {
      window.clearTimeout(skeletonTimer);
      window.clearTimeout(returnTimer);
      window.clearTimeout(timeoutTimer);
    };
  }, [chartWaitAttempt]);

  async function startAndConsumeContinuation<T>(
    start: () => Promise<T>,
    shouldConsume: () => boolean = () => true,
  ): Promise<T> {
    const response = await start();
    if (resumedTask && resumeKey && shouldConsume()) {
      void consumePendingStartTask(resumeKey);
      intentKeyRef.current = null;
    }
    return response;
  }

  function writeBaziPreviewRoute(readingId: string | null, profileVersionId?: string | null) {
    if (typeof router.replace !== "function") return;
    router.replace(baziPreviewRestoreHref(pathname, searchParams, readingId, profileVersionId));
  }

  function writeInlineReadingRoute(readingId: string | null) {
    if (typeof router.replace !== "function") return;
    router.replace(inlineReadingRestoreHref(pathname, searchParams, readingId));
  }

  function returnToInlineInput() {
    clearRecoverableReading(product.id);
    profileVersionRef.current = null;
    confirmedProfileInputRef.current = null;
    intentKeyRef.current = null;
    setInlineRecovery(null);
    setInlineRestarting(false);
    setZiweiPreviewReadingId(null);
    setLiuyaoPreviewReadingId(null);
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);
    setStage("input");
    writeInlineReadingRoute(null);
  }

  function returnToBaziInput() {
    clearBaziPreviewRecoveryState(baziPreviewReadingId);
    profileVersionRef.current = null;
    confirmedProfileInputRef.current = null;
    setBaziPreviewRecovery(null);
    intentKeyRef.current = null;
    setBaziPreviewReadingId(null);
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);
    setStage("input");
    writeBaziPreviewRoute(null);
  }

  useEffect(() => {
    if (restoredBaziReadingId && requestedProfileVersionId) {
      profileVersionRef.current = requestedProfileVersionId;
    }
  }, [restoredBaziReadingId, requestedProfileVersionId]);

  useEffect(() => {
    const profileVersionId = activeInlineRecovery?.submission.profileVersionId;
    if (profileVersionId) {
      profileVersionRef.current = profileVersionId;
    }
  }, [activeInlineRecovery?.submission.profileVersionId]);

  useEffect(() => {
    if (!shouldLoadProfiles) return;

    let active = true;
    void listProfiles()
      .then(({ profiles }) => {
        if (!active) return;
        const selectionContextChanged =
          profileSelectionContextRef.current !== resumedSelectionContext;
        profileSelectionContextRef.current = resumedSelectionContext;
        const resumedProfileAvailable =
          !resumedProfileVersionId
          || profiles.some(
            (profile) => profile.profile_version_id === resumedProfileVersionId,
          );
        setSavedProfilesError(
          selectionContextChanged && !resumedProfileAvailable
            ? "登录后未能恢复原先选择的档案，请重新读取已保存资料。"
            : null,
        );
        setSavedProfilesSignedOut(false);
        setSavedProfiles(profiles);
        setSelectedProfileVersionId((current) => {
          if (
            resumedSelectionContext
            && resumedProfileAvailable
            && resumedProfileVersionId
          ) {
            return resumedProfileVersionId;
          }
          if (
            requestedProfileVersionId &&
            profiles.some(
              (profile) => profile.profile_version_id === requestedProfileVersionId,
            )
          ) {
            return requestedProfileVersionId;
          }
          if (selectionContextChanged) {
            if (resumedProfileAvailable && resumedProfileVersionId) {
              return resumedProfileVersionId;
            }
            return resumedProfileAvailable
              ? profiles[0]?.profile_version_id ?? ""
              : "";
          }
          if (
            current &&
            profiles.some((profile) => profile.profile_version_id === current)
          ) {
            return current;
          }
          if (resumedProfileAvailable && resumedProfileVersionId) {
            return resumedProfileVersionId;
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
  }, [
    shouldLoadProfiles,
    requestedProfileVersionId,
    resumedProfileVersionId,
    resumedSelectionContext,
    savedProfilesAttempt,
  ]);

  async function confirmTaskProfile(
    nextValues: TaskFormValues,
    body: ProfileConfirmRequest,
    shouldApply: () => boolean = () => true,
  ): Promise<ProfileSummary | null> {
    let pending = pendingProfileRef.current;
    if (pending && pending.nextValues !== nextValues) {
      await discardProfileDraft(pending.draftId);
      pendingProfileRef.current = null;
      pending = null;
    }
    if (!pending) {
      const draft = await createProfileDraft(nextValues.subject.trim() || undefined);
      pending = { draftId: draft.draft_id, body, nextValues };
      pendingProfileRef.current = pending;
    }
    try {
      const profile = await confirmProfileDraft(pending.draftId, pending.body);
      pendingProfileRef.current = null;
      setCreatedProfile(profile);
      return profile;
    } catch (reason) {
      if (isProfileNameConflict(reason)) {
        if (!shouldApply()) return null;
        setNameConflict(readProfileNameConflict(reason));
        return null;
      }
      throw reason;
    }
  }

  async function startRuntimeReading(nextValues: TaskFormValues) {
    if (resumedTask && resumeKey) {
      intentKeyRef.current = { fingerprint: resumedTask.fingerprint, key: resumeKey };
    }
    if (!hasRuntimeStart(product)) {
      setStage("workbench");
      return;
    }
    if (busy) return;
    const chartAttemptId = product.id === "bazi" || product.id === "ziwei"
      ? chartWaitAttemptRef.current + 1
      : null;
    if (chartAttemptId !== null) {
      chartWaitAttemptRef.current = chartAttemptId;
      setShowChartSkeleton(false);
      setFocusChartReadyReveal(false);
      setCanReturnFromChartWait(false);
      setChartWaitAttempt(chartAttemptId);
    }
    const chartAttemptIsActive = () => (
      chartAttemptId === null || chartWaitAttemptRef.current === chartAttemptId
    );
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
        const response = await startAndConsumeContinuation(
          () => startPhysiognomyReading(payload, intent.key),
        );
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
        const response = await startAndConsumeContinuation(
          () => startFengshuiReading(payload, intent.key),
        );
        router.push(`/app/readings/${response.reading_version_id}`);
        return;
      }
      if (product.group === "natal") {
        let profileVersionId = selectedProfileVersionId;
        if (!profileVersionId) {
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
          const profileInput = profileInputFingerprint(body);
          if (
            profileVersionRef.current
            && confirmedProfileInputRef.current === profileInput
          ) {
            profileVersionId = profileVersionRef.current;
          } else {
            if (profileVersionRef.current) {
              profileVersionRef.current = null;
              confirmedProfileInputRef.current = null;
              intentKeyRef.current = null;
            }
            const profile = await confirmTaskProfile(nextValues, body, chartAttemptIsActive);
            if (!profile) return;
            profileVersionRef.current = profile.profile_version_id;
            confirmedProfileInputRef.current = profileInput;
            if (!chartAttemptIsActive()) return;
            profileVersionId = profile.profile_version_id;
          }
        }
        profileVersionRef.current = profileVersionId;

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
        const response = await startAndConsumeContinuation(
          () => (
            product.id === "bazi"
              ? startPreviewReading(payload, intent.key)
              : product.id === "luming-nayin"
                ? startLumingNayinReading(payload as LumingNayinStartRequest, intent.key)
              : product.id === "ziwei"
                ? startZiweiReading(payload, intent.key)
                : startQizhengReading(payload, intent.key)
          ),
          chartAttemptIsActive,
        );
        if (!chartAttemptIsActive()) return;
        if (chartAttemptId !== null) {
          const waitingRegion = document.querySelector(
            `[data-chart-skeleton='${product.id}']`,
          );
          setFocusChartReadyReveal(
            waitingRegion?.contains(document.activeElement) === true,
          );
        }
        if (product.id === "bazi") {
          const recovery = persistBaziPreviewRecoveryState({
            readingId: response.reading_version_id,
            profileVersionId,
            question: payload.query ?? "",
          });
          setBaziPreviewRecovery(recovery);
          setBaziPreviewReadingId(response.reading_version_id);
          setStage("workbench");
          writeBaziPreviewRoute(response.reading_version_id, profileVersionId);
        } else if (product.id === "ziwei") {
          const recovery = saveRecoverableReading(
            "ziwei",
            response.reading_version_id,
            {
              profileVersionId,
              startedAt: resolveReadingStartedAt(response.created_at),
              values: nextValues,
            },
          );
          setInlineRecovery(recovery);
          setZiweiPreviewReadingId(response.reading_version_id);
          setStage("workbench");
          writeInlineReadingRoute(response.reading_version_id);
        } else {
          router.push(`/app/readings/${response.reading_version_id}`);
        }
        return;
      }

      if (product.id === "hecan" || product.id === "canwen") {
        let profileVersionId = selectedProfileVersionId || profileVersionRef.current;
        if (!profileVersionId) {
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
          const profile = await confirmTaskProfile(nextValues, body);
          if (!profile) return;
          profileVersionId = profile.profile_version_id;
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
        const response = await startAndConsumeContinuation(() => (
          product.id === "hecan"
            ? startHecanReading(payload, intent.key)
            : startCanwenReading(payload, intent.key)
        ));
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
        const response = await startAndConsumeContinuation(
          () => startTaiyiReading(payload, intent.key),
        );
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
        const response = await startAndConsumeContinuation(
          () => startSelectionReading(payload, intent.key),
        );
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
        const response = await startAndConsumeContinuation(
          () => startLiuyaoReading(payload, intent.key),
        );
        const recovery = saveRecoverableReading(
          "liuyao",
          response.reading_version_id,
          {
            startedAt: resolveReadingStartedAt(response.created_at),
            values: nextValues,
          },
        );
        setInlineRecovery(recovery);
        setLiuyaoPreviewReadingId(response.reading_version_id);
        setStage("workbench");
        writeInlineReadingRoute(response.reading_version_id);
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
        const response = await startAndConsumeContinuation(
          () => startWenshiReading(payload, intent.key),
        );
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
        const response = await startAndConsumeContinuation(
          () => startMeihuaReading(payload, intent.key),
        );
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
      const response = await startAndConsumeContinuation(() => (
        product.id === "qimen"
          ? startQimenReading(payload, intent.key)
          : startDaliurenReading(daliurenPayload, intent.key)
      ));
      router.push(`/app/readings/${response.reading_version_id}`);
    } catch (reason) {
      if (!chartAttemptIsActive()) return;
      const mapped = mapStartReadingFailure(reason);
      const action = startReadingFailureAction(reason);
      setSubmitErrorState(mapped.state);
      setSubmitError(mapped.title);
      const intent = intentKeyRef.current;
      if (action === "login" && intent) {
        const profileVersionId =
          profileVersionRef.current?.trim()
          || selectedProfileVersionId.trim()
          || undefined;
        const storageFailure = persistPendingStartTask(intent.key, {
          productId: product.id,
          fingerprint: intent.fingerprint,
          values: {
            version: 1,
            formValues: nextValues,
            ...(profileVersionId ? { profileVersionId } : {}),
          } satisfies PendingStartFormState,
        });
        if (storageFailure) {
          setSubmitErrorState("error");
          setSubmitError(PENDING_START_WRITE_ERROR);
          setSubmitErrorAction("retry");
          setLoginIntentKey(undefined);
          return;
        }
      }
      setSubmitErrorAction(action);
      setLoginIntentKey(intent?.key);
    } finally {
      if (chartAttemptId === null || chartAttemptIsActive()) {
        setBusy(false);
        if (chartAttemptId !== null) {
          setShowChartSkeleton(false);
          setCanReturnFromChartWait(false);
          setChartWaitAttempt(null);
        }
      }
    }
  }

  function returnFromChartWait() {
    if (chartWaitAttempt === null) return;
    chartWaitAttemptRef.current += 1;
    setShowChartSkeleton(false);
    setCanReturnFromChartWait(false);
    setChartWaitAttempt(null);
    setBusy(false);
    setSubmitError(null);
    setSubmitErrorAction(null);
    setLoginIntentKey(undefined);
    setStage("input");
    window.requestAnimationFrame(() => {
      document.getElementById(`${product.id}-submit`)?.focus();
    });
  }

  async function restartInlineReading() {
    if (!activeInlineRecovery || busy) return;
    const restartValues = {
      ...(values ?? {}),
      ...activeInlineRecovery.submission.values,
    } as TaskFormValues;
    const profileVersionId = activeInlineRecovery.submission.profileVersionId;
    if (profileVersionId) {
      profileVersionRef.current = profileVersionId;
      setSelectedProfileVersionId(profileVersionId);
    }
    intentKeyRef.current = null;
    setInlineRestarting(true);
    try {
      await startRuntimeReading(restartValues);
    } finally {
      setInlineRestarting(false);
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
      confirmedProfileInputRef.current = profileInputFingerprint(pending.body);
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
  const inlineRestartFailure = submitError ? (
    <Status
      actions={(
        <>
          {submitErrorAction === "login" ? (
            <a href={loginHref}>登录后继续</a>
          ) : submitErrorAction === "retry" ? (
            <button onClick={() => void restartInlineReading()} type="button">
              再次重试（保留原资料）
            </button>
          ) : null}
        </>
      )}
      description="原任务仍保留；可按当前提示继续，或返回录入修改资料。"
      state={submitErrorState}
      title={submitError}
    />
  ) : null;

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
      <AnimatePresence initial={false}>
        {showChartSkeleton && (product.id === "bazi" || product.id === "ziwei") ? (
          <ChartStructureSkeleton
            canReturn={canReturnFromChartWait}
            key={`chart-wait-${chartWaitAttempt ?? "none"}`}
            onReturn={returnFromChartWait}
            variant={product.id}
          />
        ) : null}
      </AnimatePresence>
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
          hidden={stage !== "input" || showChartSkeleton}
        >
          {resumeStorageFailure ? (
            <Status
              actions={(
                <button
                  type="button"
                  onClick={() => setResumeReadAttempt((attempt) => attempt + 1)}
                >
                  重试恢复
                </button>
              )}
              description="请允许本网站使用会话存储，或关闭相关隐私限制后重试。"
              state="error"
              title={PENDING_START_READ_ERROR}
            />
          ) : (
            <ProductInputForm
              key={resumedTask && resumeKey ? `resume-${resumeKey}` : "input"}
              busy={busy}
              onProfileVersionChange={(profileVersionId) => {
                setSelectedProfileVersionId(profileVersionId);
                profileVersionRef.current = profileVersionId || null;
                confirmedProfileInputRef.current = null;
                intentKeyRef.current = null;
              }}
              product={product}
              profileLookupError={savedProfilesError}
              profileLookupPending={savedProfilesLoading}
              profileLookupSignedOut={savedProfilesSignedOut}
              profiles={savedProfiles}
              selectedProfileVersionId={selectedProfileVersionId}
              initialValues={values ?? resumedFormState?.formValues}
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
          )}
          <InputTrustRail product={product} />
        </div>
      ) : null}
      {stage === "workbench" && product.id !== "bazi" && product.id !== "ziwei" && product.id !== "liuyao" ? (
        <WorkbenchShell
          product={product}
          onBack={() => {
            profileVersionRef.current = null;
            confirmedProfileInputRef.current = null;
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
              onClick={returnToInlineInput}
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
                onClick={returnToInlineInput}
              >
                返回录入
              </button>
            )}
            description="盘面留在本页。登录只用于保存、历史和深读。"
            state="success"
            title="六爻盘面"
          />
          {inlineRestarting ? (
            <Status
              description="旧任务的自动检查已停止，正在用原资料创建新的任务句柄。"
              state="loading"
              title="正在重新发起"
            />
          ) : inlineRestartFailure ? (
            inlineRestartFailure
          ) : (
            <ReadingResult
              headingLevel={2}
              readingId={liuyaoPreviewReadingId}
              onRestart={activeInlineRecovery ? () => void restartInlineReading() : undefined}
              startedAt={activeInlineRecovery?.startedAt}
            />
          )}
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
        activeBaziRecovery ? (
          <ChartReadyReveal
            focusOnMount={focusChartReadyReveal}
            label={`${product.name}盘面已就绪`}
          >
            <BaziDeepTaskFlow
              onBack={returnToBaziInput}
              previewReadingId={baziPreviewReadingId}
              profileVersionId={activeBaziRecovery.profileVersionId}
              query={activeBaziRecovery.question}
            />
          </ChartReadyReveal>
        ) : !browserReady ? (
          <Status
            description="正在核对当前盘面的恢复信息，不会在确认原问题前开放深读。"
            state="loading"
            title="正在恢复八字盘面"
          />
        ) : (
          <>
            <Status
              actions={(
                <button onClick={returnToBaziInput} type="button">
                  返回录入
                </button>
              )}
              description="这份旧恢复状态没有保存原始问题。请返回录入重新提交；当前不会创建深读或结账请求。"
              state="unavailable"
              title="深读需要重新输入原问题"
            />
            <ReadingResult readingId={baziPreviewReadingId} />
          </>
        )
      ) : null}
      {stage === "workbench" && product.id === "ziwei" && !ziweiPreviewReadingId ? (
        <Status
          actions={
            <button
              type="button"
              onClick={returnToInlineInput}
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
        <ChartReadyReveal
          focusOnMount={focusChartReadyReveal}
          label={`${product.name}盘面已就绪`}
        >
          <Status
            actions={
              <button
                type="button"
                onClick={returnToInlineInput}
              >
                返回录入
              </button>
            }
            description="盘面留在本页。登录只用于保存、历史和深读。"
            state="empty"
            title="紫微盘面"
          />
          {inlineRestarting ? (
            <Status
              description="旧任务的自动检查已停止，正在用原资料创建新的任务句柄。"
              state="loading"
              title="正在重新发起"
            />
          ) : inlineRestartFailure ? (
            inlineRestartFailure
          ) : (
            <ReadingResult
              readingId={ziweiPreviewReadingId}
              onRestart={activeInlineRecovery ? () => void restartInlineReading() : undefined}
              startedAt={activeInlineRecovery?.startedAt}
            />
          )}
        </ChartReadyReveal>
      ) : null}
    </div>
  );
}
