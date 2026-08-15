import {
  accountSurfaces,
  authSurfaces,
  commerceSurfaces,
  getToolSurface,
  publicContentSurfaces,
  type AccountSurfaceSpec,
  type AuthSurfaceSpec,
  type CommerceSurfaceSpec,
  type PublicContentSurfaceSpec,
} from "@/lib/secondary-surfaces";
import type {
  UiLabPreviewKind,
  UiLabRouteCategory,
  UiLabSchemaSource,
  UiLabSchemaVersion,
  UiLabSurfaceSchemaVersion,
} from "@/lib/ui-lab-contract";
import type { ProductId } from "@/products/catalog";
import {
  VIEW_MODEL_FIXTURES,
  type ViewModelFixture,
  type ViewModelVersion,
} from "@/view-models/registry";

type UiLabFixtureBase = {
  readonly id: string;
  readonly category: UiLabRouteCategory;
  readonly routePattern: string;
  readonly title: string;
  readonly description: string;
  readonly previewKind: UiLabPreviewKind;
  readonly schemaVersion: UiLabSchemaVersion;
  readonly schemaSource: UiLabSchemaSource;
};

type RegisteredViewModelFixtureBase = UiLabFixtureBase & {
  readonly productId: ProductId;
  readonly schemaVersion: ViewModelVersion;
  readonly schemaSource: "view-model-registry";
  readonly viewModel: ViewModelFixture;
};

type ProductViewModelFixture = RegisteredViewModelFixtureBase & {
  readonly previewKind: "product-input" | "workbench";
};

export type UiLabRelationshipFixture = RegisteredViewModelFixtureBase & {
  readonly previewKind: "relationship-status";
};

type ReadingFixture = UiLabFixtureBase & {
  readonly previewKind: "reading";
  readonly productId: ProductId;
  readonly schemaVersion: "reading-document/v1";
  readonly schemaSource: "ui-lab-surface-schema";
};

type AccountFixture = UiLabFixtureBase & {
  readonly previewKind: "account";
  readonly schemaVersion: "account-surface/v1";
  readonly schemaSource: "ui-lab-surface-schema";
  readonly surface: AccountSurfaceSpec;
};

type AuthFixture = UiLabFixtureBase & {
  readonly previewKind: "auth";
  readonly schemaVersion: "auth-surface/v1";
  readonly schemaSource: "ui-lab-surface-schema";
  readonly surface: AuthSurfaceSpec;
};

type CommerceFixture = UiLabFixtureBase & {
  readonly previewKind: "commerce";
  readonly schemaVersion: "commerce-surface/v1";
  readonly schemaSource: "ui-lab-surface-schema";
  readonly surface: CommerceSurfaceSpec;
};

type PublicContentFixture = UiLabFixtureBase & {
  readonly previewKind: "public-content";
  readonly schemaVersion: "public-content-surface/v1";
  readonly schemaSource: "ui-lab-surface-schema";
  readonly surface: PublicContentSurfaceSpec;
};

export type UiLabFixture =
  | ProductViewModelFixture
  | UiLabRelationshipFixture
  | ReadingFixture
  | AccountFixture
  | AuthFixture
  | CommerceFixture
  | PublicContentFixture;

const surfaceSchema = <V extends UiLabSurfaceSchemaVersion>(version: V) => version;

function publicRouteSurface(title: string, intro: string): PublicContentSurfaceSpec {
  return {
    eyebrow: "Web 路由验收",
    title,
    intro,
    state: "unavailable",
    statusTitle: "只验收正式页面组件",
    statusDescription: "这里使用 UI Lab 的版本化 surface schema；没有接入真实内容或业务数据。",
  };
}

const accountOverviewSurface: AccountSurfaceSpec = {
  eyebrow: "个人中心",
  title: "个人中心与当前身份",
  intro: "UI Lab 只验收正式账户组件；不会读取会话、档案、任务或通知。",
  state: "need-login",
  statusTitle: "需要登录",
  statusDescription: "登录服务接通后，正式路由才会返回当前用户的数据。",
  action: { href: "/auth/login", label: "前往登录" },
};

export const UI_LAB_FIXTURES = [
  {
    id: "public-home",
    category: "public",
    routePattern: "/",
    title: "任务型首页",
    description: "检查七术、跨术、每日、工具与内容入口的正式公共页面容器。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicRouteSurface("选择要解决的事", "所有入口按用户任务组织；不直接暴露 Provider 内部键或原始结果。"),
  },
  {
    id: "public-arts",
    category: "public",
    routePattern: "/arts",
    title: "术数总览",
    description: "检查单术、双人合盘与跨术入口的产品边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicRouteSurface("术数总览", "按命、卦、相与跨术任务发现正式产品；产品输入按术数合同收口。"),
  },
  {
    id: "public-daily",
    category: "public",
    routePattern: "/daily",
    title: "每日",
    description: "检查每日真实数据不可用时的正式边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicContentSurfaces.daily,
  },
  {
    id: "public-tools",
    category: "public",
    routePattern: "/tools",
    title: "工具总览",
    description: "检查六项冻结工具的入口与适配状态。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicContentSurfaces.tools,
  },
  {
    id: "tool-time-check",
    category: "public",
    routePattern: "/tools/time-check",
    title: "寻时定盘",
    description: "检查未知时辰辅助流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("time-check"),
  },
  {
    id: "tool-chart-similarity",
    category: "public",
    routePattern: "/tools/chart-similarity",
    title: "同盘匹配",
    description: "检查盘面相似流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("chart-similarity"),
  },
  {
    id: "tool-rhythm",
    category: "public",
    routePattern: "/tools/rhythm",
    title: "本命音律",
    description: "检查本命音律流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("rhythm"),
  },
  {
    id: "tool-five-elements",
    category: "public",
    routePattern: "/tools/five-elements",
    title: "五行事实与调候",
    description: "检查五行事实与调候流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("five-elements"),
  },
  {
    id: "tool-dream",
    category: "public",
    routePattern: "/tools/dream",
    title: "解梦",
    description: "检查解梦流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("dream"),
  },
  {
    id: "tool-name",
    category: "public",
    routePattern: "/tools/name",
    title: "姓名分析",
    description: "检查姓名分析流程的能力边界。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: getToolSurface("name"),
  },
  {
    id: "public-library",
    category: "public",
    routePattern: "/library",
    title: "知识内容索引",
    description: "检查内容为空与来源说明。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicContentSurfaces.library,
  },
  {
    id: "public-article",
    category: "public",
    routePattern: "/library/[slug]",
    title: "公开文章模式",
    description: "检查动态文章路由不猜测未发布内容。",
    previewKind: "public-content",
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: publicContentSurfaces.article,
  },
  ...([
    ["public-about", "/about", "关于与边界", "说明产品方法、团队与能力边界。"],
    ["public-pricing", "/pricing", "价格与交付", "说明免费范围、真实 Offer 与交付。"],
    ["public-methodology", "/methodology", "方法与证据", "说明先算后讲、证据、AI 与适用边界。"],
    ["public-support", "/support", "支持中心", "说明账号、任务、订单、退款与数据帮助。"],
    ["public-privacy", "/privacy", "隐私政策", "检查版本化隐私政策页面。"],
    ["public-terms", "/terms", "服务条款", "检查版本化服务与付费条款页面。"],
  ] as const).map(([id, routePattern, title, intro]) => ({
    id,
    category: "public" as const,
    routePattern,
    title,
    description: intro,
    previewKind: "public-content" as const,
    schemaVersion: surfaceSchema("public-content-surface/v1"),
    schemaSource: "ui-lab-surface-schema" as const,
    surface: publicRouteSurface(title, intro),
  })),
  {
    id: "bazi-input",
    category: "product",
    routePattern: "/bazi",
    title: "八字任务录入",
    description: "使用正式 ProductInputForm 检查八字录入与校验。",
    previewKind: "product-input",
    productId: "bazi",
    schemaVersion: "bazi-chart/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["bazi-chart/v1"],
  },
  {
    id: "bazi-hepan",
    category: "product",
    routePattern: "/bazi/hepan",
    title: "八字双人合盘",
    description: "使用正式 Status 呈现合盘 ViewModel 接入边界，避免在验收台嵌套整页壳。",
    previewKind: "relationship-status",
    productId: "bazi",
    schemaVersion: "bazi-relationship/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["bazi-relationship/v1"],
  },
  {
    id: "ziwei-input",
    category: "product",
    routePattern: "/ziwei",
    title: "紫微任务录入",
    description: "使用正式 ProductInputForm 检查紫微录入与校验。",
    previewKind: "product-input",
    productId: "ziwei",
    schemaVersion: "ziwei-chart/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["ziwei-chart/v1"],
  },
  {
    id: "ziwei-hepan",
    category: "product",
    routePattern: "/ziwei/hepan",
    title: "紫微双人合盘",
    description: "使用正式 Status 呈现合盘 ViewModel 接入边界。",
    previewKind: "relationship-status",
    productId: "ziwei",
    schemaVersion: "ziwei-relationship/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["ziwei-relationship/v1"],
  },
  {
    id: "qizheng-input",
    category: "product",
    routePattern: "/qizheng",
    title: "七政任务录入",
    description: "使用正式 ProductInputForm 检查七政录入与校验。",
    previewKind: "product-input",
    productId: "qizheng",
    schemaVersion: "qizheng-chart/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["qizheng-chart/v1"],
  },
  {
    id: "qizheng-hepan",
    category: "product",
    routePattern: "/qizheng/hepan",
    title: "七政双人合盘",
    description: "使用正式 Status 呈现合盘 ViewModel 接入边界。",
    previewKind: "relationship-status",
    productId: "qizheng",
    schemaVersion: "qizheng-relationship/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["qizheng-relationship/v1"],
  },
  ...([
    ["liuyao-input", "/liuyao", "六爻", "liuyao", "liuyao-chart/v1"],
    ["qimen-input", "/qimen", "奇门", "qimen", "qimen-chart/v1"],
    ["daliuren-input", "/daliuren", "大六壬", "daliuren", "daliuren-chart/v1"],
    ["jianxiang-input", "/jianxiang", "见相", "jianxiang", "physiognomy-view/v1"],
    ["hecan-input", "/hecan", "命盘合参", "hecan", "hecan-view/v1"],
    ["wenshi-input", "/wenshi", "问事合参", "wenshi", "wenshi-view/v1"],
    ["canwen-input", "/canwen", "多盘问答", "canwen", "canwen-view/v1"],
  ] as const).map(([id, routePattern, name, productId, schemaVersion]) => ({
    id,
    category: "product" as const,
    routePattern,
    title: `${name}任务录入`,
    description: `使用正式 ProductInputForm 检查${name}输入与校验。`,
    previewKind: "product-input" as const,
    productId,
    schemaVersion,
    schemaSource: "view-model-registry" as const,
    viewModel: VIEW_MODEL_FIXTURES[schemaVersion],
  })),
  {
    id: "workbench-handle",
    category: "product",
    routePattern: "/workbench/[handle]",
    title: "任务恢复工作台",
    description: "使用正式 WorkbenchShell 与 ReadingShell 检查恢复后的任务布局。",
    previewKind: "workbench",
    productId: "bazi",
    schemaVersion: "bazi-chart/v1",
    schemaSource: "view-model-registry",
    viewModel: VIEW_MODEL_FIXTURES["bazi-chart/v1"],
  },
  {
    id: "checkout-order",
    category: "product",
    routePattern: "/checkout/[orderId]",
    title: "订单结账",
    description: "使用正式 CommerceSurface 检查订单快照与服务端支付事实边界。",
    previewKind: "commerce",
    schemaVersion: surfaceSchema("commerce-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: commerceSurfaces.order,
  },
  {
    id: "share-token",
    category: "product",
    routePattern: "/share/[shareId]",
    title: "限时分享",
    description: "使用正式 CommerceSurface 检查分享隐私投影边界。",
    previewKind: "commerce",
    schemaVersion: surfaceSchema("commerce-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: commerceSurfaces.share,
  },
  {
    id: "invite-code",
    category: "product",
    routePattern: "/invite/[code]",
    title: "邀请活动落地页",
    description: "使用正式 CommerceSurface 检查活动与归因边界。",
    previewKind: "commerce",
    schemaVersion: surfaceSchema("commerce-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: commerceSurfaces.invite,
  },
  ...([
    ["auth-login", "/auth/login", "登录", authSurfaces.login],
    ["auth-register", "/auth/register", "注册", authSurfaces.register],
    ["auth-verify", "/auth/verify", "验证身份", authSurfaces.verify],
    ["auth-set-password", "/auth/set-password", "设置密码", authSurfaces.setPassword],
    ["auth-recover", "/auth/recover", "找回账号", authSurfaces.recover],
    ["auth-consent", "/auth/consent", "政策同意", authSurfaces.consent],
  ] as const).map(([id, routePattern, title, surface]) => ({
    id,
    category: "auth" as const,
    routePattern,
    title,
    description: `使用正式 AuthSurface 检查${title}流程。`,
    previewKind: "auth" as const,
    schemaVersion: surfaceSchema("auth-surface/v1"),
    schemaSource: "ui-lab-surface-schema" as const,
    surface,
  })),
  {
    id: "account-overview",
    category: "account",
    routePattern: "/account",
    title: "个人中心",
    description: "使用正式 AccountSurface 检查身份与账户入口。",
    previewKind: "account",
    schemaVersion: surfaceSchema("account-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: accountOverviewSurface,
  },
  {
    id: "account-profiles",
    category: "account",
    routePattern: "/account/profiles",
    title: "受测人档案",
    description: "使用正式 AccountSurface 检查档案入口。",
    previewKind: "account",
    schemaVersion: surfaceSchema("account-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: accountSurfaces.profiles,
  },
  {
    id: "account-profile-detail",
    category: "account",
    routePattern: "/account/profiles/[profileId]",
    title: "档案详情",
    description: "使用正式 AccountSurface 检查档案版本边界。",
    previewKind: "account",
    schemaVersion: surfaceSchema("account-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: accountSurfaces.profileDetail,
  },
  {
    id: "account-history",
    category: "account",
    routePattern: "/account/history",
    title: "推演历史",
    description: "使用正式 AccountSurface 检查任务根与版本入口。",
    previewKind: "account",
    schemaVersion: surfaceSchema("account-surface/v1"),
    schemaSource: "ui-lab-surface-schema",
    surface: accountSurfaces.history,
  },
  {
    id: "account-history-detail",
    category: "account",
    routePattern: "/account/history/[rootId]",
    title: "历史报告阅读",
    description: "使用正式 ReadingShell 检查连续报告的阅读结构。",
    previewKind: "reading",
    productId: "bazi",
    schemaVersion: surfaceSchema("reading-document/v1"),
    schemaSource: "ui-lab-surface-schema",
  },
  ...([
    ["account-orders", "/account/orders", "订单", accountSurfaces.orders],
    ["account-entitlements", "/account/entitlements", "权益", accountSurfaces.entitlements],
    ["account-invitations", "/account/invitations", "邀请", accountSurfaces.invitations],
    ["account-notifications", "/account/notifications", "通知", accountSurfaces.notifications],
    ["account-settings", "/account/settings", "设置", accountSurfaces.settings],
    ["account-security", "/account/settings/security", "账户安全", accountSurfaces.security],
    ["account-preferences", "/account/settings/preferences", "通知偏好", accountSurfaces.preferences],
    ["account-privacy-data", "/account/settings/privacy-data", "隐私与数据", accountSurfaces.privacyData],
    ["account-data-rights", "/account/data-rights", "数据权利", accountSurfaces.dataRights],
  ] as const).map(([id, routePattern, title, surface]) => ({
    id,
    category: "account" as const,
    routePattern,
    title,
    description: `使用正式 AccountSurface 检查${title}页面。`,
    previewKind: "account" as const,
    schemaVersion: surfaceSchema("account-surface/v1"),
    schemaSource: "ui-lab-surface-schema" as const,
    surface,
  })),
] as const satisfies readonly UiLabFixture[];

export type UiLabFixtureId = (typeof UI_LAB_FIXTURES)[number]["id"];
