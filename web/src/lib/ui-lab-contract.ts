import type { StatusState } from "@/components/ui/status";
import type { ProductId } from "@/products/catalog";
import type { ViewModelVersion } from "@/view-models/registry";

export const UI_LAB_STATES = [
  "pristine",
  "filled",
  "validation-error",
  "submitting",
  "loading",
  "camera-prompt",
  "camera-allowed",
  "camera-denied",
  "photo-selected",
  "photo-cropping",
  "photo-rotating",
  "photo-quality-failed",
  "photo-retake",
  "observation-failed",
  "observation-processing",
  "source-expiring",
  "archive-consent",
  "source-deleting",
  "source-deleted",
  "source-expired-result-ready",
  "empty",
  "ready",
  "free-summary",
  "locked",
  "need-login",
  "need-input",
  "queued",
  "preparing",
  "generating",
  "validating",
  "accepted",
  "delayed",
  "failed",
  "follow-up",
  "unauthorized",
  "forbidden",
  "unavailable",
  "maintenance",
  "payment-confirming",
  "payment-success",
  "payment-failed",
  "refund",
  "reversed",
  "invite-planned",
  "invite-active",
  "invite-paused",
  "invite-full",
  "invite-ended",
  "invite-invalid",
  "invite-self",
] as const;

export type UiLabState = (typeof UI_LAB_STATES)[number];

export type UiLabTone = "neutral" | "info" | "success" | "warning" | "danger";

export const UI_LAB_STATE_DETAILS = {
  pristine: { label: "初始待填", description: "尚未填写或提交任何资料。", tone: "neutral" },
  filled: { label: "已填写", description: "资料已填写，等待用户确认。", tone: "info" },
  "validation-error": { label: "校验失败", description: "字段有明确问题，可就近修改。", tone: "danger" },
  submitting: { label: "提交中", description: "操作正在提交，重复触发已停用。", tone: "info" },
  loading: { label: "加载中", description: "正在读取已有任务或页面资料。", tone: "info" },
  "camera-prompt": { label: "相机权限未询问", description: "当前不会擅自请求相机权限；用户可以改用本地文件。", tone: "neutral" },
  "camera-allowed": { label: "相机权限已允许", description: "相机采集仅产生本次见相所需的本地媒体，仍需独立同意和质量检查。", tone: "success" },
  "camera-denied": { label: "相机权限被拒绝", description: "相机被拒绝后仍保留本地文件入口，不阻断用户完成资料补充。", tone: "warning" },
  "photo-selected": { label: "本地照片已选择", description: "只确认本地文件已选择；尚未上传、保存或生成观察结论。", tone: "success" },
  "photo-cropping": { label: "照片裁切中", description: "裁切结果尚未提交；界面不能把预览当作已保存媒体。", tone: "info" },
  "photo-rotating": { label: "照片旋转中", description: "旋转只改变待处理媒体方向，不产生身份识别或命理结论。", tone: "info" },
  "photo-quality-failed": { label: "照片质量不合格", description: "质量检查未通过，需要重新拍摄或选择文件；不会进入观察流程。", tone: "danger" },
  "photo-retake": { label: "等待重拍", description: "用户可以重新拍摄或选择文件，原失败媒体不会被当作有效输入。", tone: "warning" },
  "observation-failed": { label: "观察失败", description: "没有可展示的结构化观察；用户可补资料或重试，不显示猜测结果。", tone: "danger" },
  "observation-processing": { label: "观察处理中", description: "只展示处理状态和版本边界，不提前显示视觉或命理结论。", tone: "info" },
  "source-expiring": { label: "原图即将过期", description: "页面明确提示媒体生命周期；结构化观察和结果是否保留按授权与政策处理。", tone: "warning" },
  "archive-consent": { label: "等待主动入档", description: "长期保存必须由用户另行同意；未确认时不写入见相档案。", tone: "warning" },
  "source-deleting": { label: "原图删除中", description: "删除请求正在处理；页面不再展示原图或衍生图。", tone: "info" },
  "source-deleted": { label: "原图已删除", description: "原图及衍生图不可在正常产品界面恢复；可按政策保留结构化结果。", tone: "success" },
  "source-expired-result-ready": { label: "原图已过期，结果可查看", description: "原图不可查看；只有已授权、可审计的结构化观察与结果继续展示。", tone: "success" },
  empty: { label: "暂无内容", description: "当前范围内没有可展示记录。", tone: "neutral" },
  ready: { label: "已就绪", description: "界面与所需资料均可继续操作。", tone: "success" },
  "free-summary": { label: "免费摘要", description: "免费结果已就绪，深读仍是独立交付。", tone: "success" },
  locked: { label: "已锁定", description: "当前版本已固定，修改需要创建新任务。", tone: "warning" },
  "need-login": { label: "需要登录", description: "保存或跨设备继续前需要登录。", tone: "warning" },
  "need-input": { label: "需要补充资料", description: "继续前需要补齐页面列出的资料。", tone: "warning" },
  queued: { label: "已进入队列", description: "任务已接收，等待开始处理。", tone: "info" },
  preparing: { label: "整理事实", description: "正在整理确定性事实与版本信息。", tone: "info" },
  generating: { label: "生成解读", description: "正在生成结构化解读，可稍后回来查看。", tone: "info" },
  validating: { label: "文字校验", description: "正在核对引用、边界与用户可见文案。", tone: "info" },
  accepted: { label: "已交付", description: "本次版本已经验收并固定保存。", tone: "success" },
  delayed: { label: "交付延迟", description: "任务仍会继续，完成后会发送通知。", tone: "warning" },
  failed: { label: "处理失败", description: "本次处理未完成，可按页面指引恢复。", tone: "danger" },
  "follow-up": { label: "可追问", description: "可以围绕当前报告提交同范围追问。", tone: "success" },
  unauthorized: { label: "登录已失效", description: "重新登录后可返回当前任务。", tone: "warning" },
  forbidden: { label: "无权访问", description: "当前身份没有查看或操作权限。", tone: "danger" },
  unavailable: { label: "暂不可用", description: "能力尚未接入，页面不会伪造结果。", tone: "neutral" },
  maintenance: { label: "维护中", description: "暂不接收新任务，已有记录仍可查看。", tone: "warning" },
  "payment-confirming": { label: "支付确认中", description: "等待服务端确认支付事实。", tone: "info" },
  "payment-success": { label: "支付成功", description: "服务端已确认支付并更新交付状态。", tone: "success" },
  "payment-failed": { label: "支付失败", description: "没有确认到账，可更换方式或重试。", tone: "danger" },
  refund: { label: "退款处理中", description: "退款申请已受理，等待渠道结果。", tone: "warning" },
  reversed: { label: "已冲正", description: "相关权益已按账本事件完成冲正。", tone: "warning" },
  "invite-planned": { label: "活动计划中", description: "活动尚未开始，不能建立归因。", tone: "neutral" },
  "invite-active": { label: "活动进行中", description: "当前邀请活动可建立临时归因。", tone: "success" },
  "invite-paused": { label: "活动已暂停", description: "暂停期间不接收新的归因或合格支付。", tone: "warning" },
  "invite-full": { label: "名额已满", description: "付款前已说明本单不参加活动。", tone: "warning" },
  "invite-ended": { label: "活动已结束", description: "历史奖励仍可在账户中查看。", tone: "neutral" },
  "invite-invalid": { label: "邀请无效", description: "链接无效，不会写入邀请归因。", tone: "danger" },
  "invite-self": { label: "不可自邀", description: "邀请人与受邀账号不能是同一用户。", tone: "danger" },
} as const satisfies Record<UiLabState, { label: string; description: string; tone: UiLabTone }>;

/**
 * Every UI Lab state resolves to the shared production Status vocabulary.
 * `pristine` (and `filled` for product forms) render the production surface;
 * every other state uses this map to replace that normal body.
 */
export const UI_LAB_STATUS_BY_STATE = {
  pristine: "empty",
  filled: "success",
  "validation-error": "error",
  submitting: "processing",
  loading: "loading",
  "camera-prompt": "empty",
  "camera-allowed": "success",
  "camera-denied": "unavailable",
  "photo-selected": "success",
  "photo-cropping": "processing",
  "photo-rotating": "processing",
  "photo-quality-failed": "error",
  "photo-retake": "locked",
  "observation-failed": "error",
  "observation-processing": "processing",
  "source-expiring": "processing",
  "archive-consent": "locked",
  "source-deleting": "processing",
  "source-deleted": "success",
  "source-expired-result-ready": "success",
  empty: "empty",
  ready: "success",
  "free-summary": "success",
  locked: "locked",
  "need-login": "unauthorized",
  "need-input": "locked",
  queued: "processing",
  preparing: "processing",
  generating: "processing",
  validating: "processing",
  accepted: "success",
  delayed: "processing",
  failed: "error",
  "follow-up": "success",
  unauthorized: "unauthorized",
  forbidden: "unauthorized",
  unavailable: "unavailable",
  maintenance: "unavailable",
  "payment-confirming": "processing",
  "payment-success": "success",
  "payment-failed": "error",
  refund: "processing",
  reversed: "locked",
  "invite-planned": "empty",
  "invite-active": "success",
  "invite-paused": "locked",
  "invite-full": "locked",
  "invite-ended": "empty",
  "invite-invalid": "error",
  "invite-self": "error",
} as const satisfies Record<UiLabState, StatusState>;

export const UI_LAB_STATE_GROUPS = [
  { label: "录入与读取", states: ["pristine", "filled", "validation-error", "submitting", "loading", "empty", "ready", "free-summary"] },
  { label: "见相媒体与生命周期", states: ["camera-prompt", "camera-allowed", "camera-denied", "photo-selected", "photo-cropping", "photo-rotating", "photo-quality-failed", "photo-retake", "observation-failed", "observation-processing", "source-expiring", "archive-consent", "source-deleting", "source-deleted", "source-expired-result-ready"] },
  { label: "身份与权限", states: ["locked", "need-login", "need-input", "unauthorized", "forbidden"] },
  { label: "任务交付", states: ["queued", "preparing", "generating", "validating", "accepted", "delayed", "failed", "follow-up"] },
  { label: "可用性", states: ["unavailable", "maintenance"] },
  { label: "商业", states: ["payment-confirming", "payment-success", "payment-failed", "refund", "reversed"] },
  { label: "邀请", states: ["invite-planned", "invite-active", "invite-paused", "invite-full", "invite-ended", "invite-invalid", "invite-self"] },
] as const satisfies ReadonlyArray<{ label: string; states: ReadonlyArray<UiLabState> }>;

export const UI_LAB_VIEWPORTS = [360, 768, 1024, 1440] as const;

export type UiLabViewport = (typeof UI_LAB_VIEWPORTS)[number];

export const UI_LAB_ROLES = ["guest", "member", "test-account"] as const;

export type UiLabRole = (typeof UI_LAB_ROLES)[number];

export const UI_LAB_ROLE_LABELS = {
  guest: "游客",
  member: "登录用户",
  "test-account": "授权测试账号",
} as const satisfies Record<UiLabRole, string>;

export const UI_LAB_CAPABILITIES = [
  {
    id: "ui-prebuilt",
    label: "UI 已预制",
    uiStatus: "可验收",
    algorithmStatus: "未接入",
    description: "只使用明确标记的演示 Fixture。",
  },
  {
    id: "adapting",
    label: "算法适配中",
    uiStatus: "可验收",
    algorithmStatus: "适配中",
    description: "正常路由只能说明适配中，不能显示假结果。",
  },
  {
    id: "internal-test",
    label: "内部测试",
    uiStatus: "可验收",
    algorithmStatus: "测试账号可用",
    description: "仅授权测试账号可运行真实能力。",
  },
  {
    id: "public",
    label: "公开开放",
    uiStatus: "可验收",
    algorithmStatus: "已公开",
    description: "公开状态仍以真实服务端事实为准。",
  },
  {
    id: "paused",
    label: "暂停服务",
    uiStatus: "历史可读",
    algorithmStatus: "暂停新任务",
    description: "暂停不改写已有盘面、订单或报告。",
  },
] as const;

export type UiLabCapability = (typeof UI_LAB_CAPABILITIES)[number];
export type UiLabCapabilityId = UiLabCapability["id"];

export const UI_LAB_ROUTE_CATEGORIES = ["public", "product", "auth", "account"] as const;

export type UiLabRouteCategory = (typeof UI_LAB_ROUTE_CATEGORIES)[number];

export const UI_LAB_ROUTE_CATEGORY_LABELS = {
  public: "公共与内容",
  product: "产品与交付",
  auth: "身份",
  account: "账户",
} as const satisfies Record<UiLabRouteCategory, string>;

export const UI_LAB_SURFACE_SCHEMA_VERSIONS = [
  "public-content-surface/v1",
  "auth-surface/v1",
  "account-surface/v1",
  "commerce-surface/v1",
  "reading-document/v1",
] as const;

export type UiLabSurfaceSchemaVersion = (typeof UI_LAB_SURFACE_SCHEMA_VERSIONS)[number];
export type UiLabSchemaVersion = ViewModelVersion | UiLabSurfaceSchemaVersion;
export type UiLabSchemaSource = "view-model-registry" | "ui-lab-surface-schema";

export type UiLabPreviewKind =
  | "product-input"
  | "workbench"
  | "reading"
  | "relationship-status"
  | "account"
  | "auth"
  | "commerce"
  | "public-content";

export function uiLabRendersProductionSurface(
  previewKind: UiLabPreviewKind,
  state: UiLabState,
): boolean {
  if (previewKind === "relationship-status") return false;
  if (state === "pristine") return true;
  return previewKind === "product-input" && state === "filled";
}

export type UiLabCapabilityGate = {
  readonly state: Extract<StatusState, "unavailable" | "unauthorized">;
  readonly title: string;
  readonly description: string;
};

export function uiLabCapabilityGate(
  previewKind: UiLabPreviewKind,
  role: UiLabRole,
  capabilityId: UiLabCapabilityId,
): UiLabCapabilityGate | null {
  const acceptsNewCapability =
    previewKind === "product-input" || previewKind === "relationship-status";

  if (!acceptsNewCapability) return null;

  if (capabilityId === "internal-test" && role !== "test-account") {
    return {
      state: "unauthorized",
      title: "仅授权测试账号可用",
      description: "当前能力只允许授权测试账号运行；普通用户不会创建任务或消耗权益。",
    };
  }

  if (capabilityId === "paused") {
    return {
      state: "unavailable",
      title: "新任务暂时停止",
      description: "服务暂停期间不接收新的输入；已有盘面、报告和历史仍按原权限查看。",
    };
  }

  return null;
}

export function uiLabRendersFullProductionPage(
  previewKind: UiLabPreviewKind,
  state: UiLabState,
): boolean {
  if (!uiLabRendersProductionSurface(previewKind, state)) return false;
  return previewKind === "auth"
    || previewKind === "commerce"
    || previewKind === "public-content";
}

export type UiLabProductPreview = {
  readonly previewKind: "product-input" | "workbench" | "reading" | "relationship-status";
  readonly productId: ProductId;
};
