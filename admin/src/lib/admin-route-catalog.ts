export type AdminRouteState = "prebuilt" | "unavailable";
export type AdminRouteSurface = "list" | "detail" | "operations" | "health" | "settings";

export type AdminRouteDefinition = {
  path: string;
  label: string;
  group: string;
  duty: string;
  state: AdminRouteState;
  surface: AdminRouteSurface;
  navigation?: boolean;
};

type AdminRouteInput = Omit<AdminRouteDefinition, "surface"> & {
  surface?: AdminRouteSurface;
};

const unavailable = "真实平台数据尚未接入；当前只展示可审计的预制状态。";
const identityRead = "读取授权可见的用户、身份、设备、同意与 Subject 业务资料；不展示密码、密文或密钥材料。";
const dataRightsRead = "读取关闭队列；执行动作受服务端等待期、角色、CSRF 与审计约束。";
const catalogLive = "读取真实 Catalog 商品族、版本和报价；命令受服务端 RBAC、CSRF 与审计约束。";
const commerceRead = "只读本地商业事实；页面不把未接入的渠道状态当作到账或审批结果。";
const entitlementsLive = "读取追加式权益事件；发放、补偿与撤回受服务端角色、CSRF、原因和审计约束。";
const referralsRead = "读取活动、活动码、归因和奖励事实；不展示访客识别哈希，也不伪造申诉审批。";
const reconciliationLive = "读取对账批次与差异；执行只接受已验签归一化快照并写入审计。";
const notificationsLive = "读取 Outbox 投递事实；重试受角色、CSRF、原因和审计约束。";
const auditRead = "只读服务端脱敏审计事实；不展示任意 metadata 或通知正文。";
const sessionsLive = "读取员工会话元数据；强退受 superadmin、CSRF、原因和审计约束。";
const staffLive = "读取员工目录；状态、角色和密码重置受 superadmin、CSRF、原因和审计约束。";
const settingsRead = "只读非秘密运行配置；不展示数据库连接、身份密钥或其他凭据。";
const healthRead = "读取 readiness 和依赖状态；未就绪时明确显示 unavailable，不伪造正常指标。";
const cmsRead = "读取真实 CMS 最新版本元数据；列表不批量返回正文，内容命令仍由服务端编辑权限约束。";
const readingsRead = "读取 ReadingVersion 的能力、版本、状态和维度数量；不展示出生输入、horizon、object 或报告正文。";
const readingJobsRead = "读取持久化解读任务元数据；不展示出生输入、输出合同、lease token 或模型 payload。";
const runtimeRead = "读取真实 RuntimeRelease 登记元数据；不展示 manifest/image digest、Provider 凭据或虚构健康状态。";
const modelRead = "读取真实 GenerationAttempt 的 Model/Guard 回执元数据；不展示请求指纹、profile digest、token 用量、价格明细或原始载荷。";
const capabilityRead = "读取版本化产品能力策略；区分 PUBLIC 产品入口与 INTERNAL_TEST Provider，不把策略当成 Runtime 健康或生产准入。";
const supportCasesLive = "读取客服案件申请；客服/超级管理员可提交申请，补偿、退款和状态处理仍由受控服务负责。";
const appealsLive = "读取真实邀请申诉与风险信号；客服可提交申请，纠错须由两位不同财务/超级管理员审批并追加账本事件。";

const ADMIN_ROUTE_INPUTS: readonly AdminRouteInput[] = [
  {
    path: "/",
    label: "根入口",
    group: "总览",
    duty: "根路径兼容入口，实际总览位于 /dashboard。",
    state: "prebuilt",
    navigation: false,
  },
  {
    path: "/login",
    label: "员工登录",
    group: "身份",
    duty: "员工账号与用户账号分离。",
    state: "prebuilt",
    navigation: false,
  },
  { path: "/dashboard", label: "总览", group: "总览", duty: "看待办、看异常，不讲故事。", state: "prebuilt" },
  { path: "/users", label: "用户与身份", group: "用户与数据", duty: identityRead, state: "prebuilt" },
  { path: "/users/[id]", label: "用户详情", group: "用户与数据", duty: identityRead, state: "prebuilt", surface: "detail" },
  { path: "/subjects", label: "Subject 与资料版本", group: "用户与数据", duty: identityRead, state: "prebuilt" },
  { path: "/subjects/[id]", label: "Subject 详情", group: "用户与数据", duty: identityRead, state: "prebuilt", surface: "detail" },
  { path: "/data-rights", label: "数据权利", group: "用户与数据", duty: dataRightsRead, state: "prebuilt" },
  { path: "/support-cases", label: "客服案件", group: "用户与数据", duty: supportCasesLive, state: "prebuilt" },
  { path: "/products", label: "商品与报价", group: "产品与内容", duty: catalogLive, state: "prebuilt" },
  { path: "/products/[id]/versions", label: "商品版本", group: "产品与内容", duty: catalogLive, state: "prebuilt", surface: "detail" },
  { path: "/capabilities", label: "能力发布", group: "产品与内容", duty: capabilityRead, state: "prebuilt", surface: "operations" },
  { path: "/cms/pages", label: "CMS 页面", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/cms/daily", label: "CMS 每日", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/cms/tools", label: "CMS 工具", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/cms/library", label: "CMS 知识", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/cms/help", label: "CMS 帮助", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/cms/policies", label: "CMS 政策", group: "产品与内容", duty: cmsRead, state: "prebuilt" },
  { path: "/charts", label: "盘面", group: "排盘与解读", duty: readingsRead, state: "prebuilt" },
  { path: "/readings", label: "报告", group: "排盘与解读", duty: readingsRead, state: "prebuilt" },
  { path: "/readings/[id]", label: "报告详情", group: "排盘与解读", duty: readingsRead, state: "prebuilt", surface: "detail" },
  { path: "/reading-jobs", label: "解读任务", group: "排盘与解读", duty: readingJobsRead, state: "prebuilt", surface: "operations" },
  { path: "/verifications", label: "逐条核对", group: "排盘与解读", duty: readingJobsRead, state: "prebuilt" },
  { path: "/observations", label: "见相观察", group: "排盘与解读", duty: unavailable, state: "unavailable" },
  { path: "/runtime", label: "Runtime 与 Provider", group: "排盘与解读", duty: runtimeRead, state: "prebuilt", surface: "operations" },
  { path: "/model-profiles", label: "Model 与 Guard", group: "排盘与解读", duty: modelRead, state: "prebuilt", surface: "operations" },
  { path: "/orders", label: "订单", group: "商业运营", duty: commerceRead, state: "prebuilt" },
  { path: "/payments", label: "支付", group: "商业运营", duty: commerceRead, state: "prebuilt" },
  { path: "/refunds", label: "退款", group: "商业运营", duty: commerceRead, state: "prebuilt" },
  { path: "/reconciliation", label: "对账", group: "商业运营", duty: reconciliationLive, state: "prebuilt" },
  { path: "/entitlements", label: "权益账本", group: "商业运营", duty: entitlementsLive, state: "prebuilt" },
  { path: "/referrals", label: "邀请活动", group: "商业运营", duty: referralsRead, state: "prebuilt" },
  { path: "/referrals/[id]", label: "邀请活动详情", group: "商业运营", duty: referralsRead, state: "prebuilt", surface: "detail" },
  { path: "/appeals", label: "邀请申诉", group: "商业运营", duty: appealsLive, state: "prebuilt" },
  { path: "/staff", label: "员工与角色", group: "系统与审计", duty: staffLive, state: "prebuilt" },
  { path: "/sessions", label: "会话", group: "系统与审计", duty: sessionsLive, state: "prebuilt" },
  { path: "/notifications", label: "通知", group: "系统与审计", duty: notificationsLive, state: "prebuilt" },
  { path: "/audit", label: "审计日志", group: "系统与审计", duty: auditRead, state: "prebuilt" },
  { path: "/settings", label: "系统设置", group: "系统与审计", duty: settingsRead, state: "prebuilt", surface: "settings" },
  { path: "/health", label: "健康检查", group: "系统与审计", duty: healthRead, state: "prebuilt", surface: "health" },
];

export const ADMIN_ROUTE_CATALOG: readonly AdminRouteDefinition[] =
  ADMIN_ROUTE_INPUTS.map((route) => ({ surface: "list", ...route }));

function matchesRoute(pattern: string, pathname: string): boolean {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathnameParts = pathname.split("/").filter(Boolean);
  if (patternParts.length !== pathnameParts.length) return false;
  return patternParts.every((part, index) => part.startsWith("[") || part === pathnameParts[index]);
}

export function resolveAdminRoute(pathname: string): AdminRouteDefinition | null {
  const normalized = pathname.split("?", 1)[0] || "/";
  return ADMIN_ROUTE_CATALOG.find((route) => matchesRoute(route.path, normalized)) ?? null;
}
