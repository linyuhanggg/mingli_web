import type { AdminRouteDefinition } from "@/lib/admin-route-catalog";

export type AdminCatalogState =
  | "ready"
  | "loading"
  | "empty"
  | "error"
  | "forbidden"
  | "unavailable"
  | "maintenance";

export type AdminCapabilityState =
  | "UI_PREBUILT"
  | "ADAPTING"
  | "INTERNAL_TEST"
  | "PUBLIC"
  | "PAUSED";

export type AdminWriteOperationState =
  | "无权限"
  | "只读"
  | "确认"
  | "原因"
  | "保存中"
  | "成功"
  | "验证失败"
  | "版本冲突"
  | "对象已变化"
  | "审计完成";

export type AdminCatalogRecordV1 = {
  id: string;
  primary: string;
  secondary: string;
  status: string;
  updatedAt: string;
  owner: string;
  cells: Readonly<Record<string, string>>;
  details: readonly { label: string; value: string }[];
};

export type AdminCatalogColumnV1 = {
  key: string;
  header: string;
  sortable?: boolean;
};

export type AdminCatalogViewModelV1 = {
  schema: "admin-catalog/v1";
  source: "live" | "fixture";
  route: AdminRouteDefinition;
  requestedPath: string;
  state: AdminCatalogState;
  capabilityState: AdminCapabilityState;
  entityLabel: string;
  filterLabel: string;
  actionLabel: string;
  notice: string;
  columns: readonly AdminCatalogColumnV1[];
  records: readonly AdminCatalogRecordV1[];
};

export type AdminCatalogApiOffer = {
  id: string;
  product_version_id: string;
  channel: string;
  channel_sku: string;
  price_minor: number;
  currency: string;
  enabled: boolean;
  created_at: string;
};

export type AdminCatalogApiVersion = {
  id: string;
  family_id: string;
  version: string;
  price_minor: number;
  currency: string;
  contract_version: string;
  follow_up_count: number;
  follow_up_window_seconds: number;
  status: string;
  created_at: string;
  offers: readonly AdminCatalogApiOffer[];
};

export type AdminCatalogApiFamily = {
  id: string;
  key: string;
  label: string;
  status: string;
  created_at: string;
  versions: readonly AdminCatalogApiVersion[];
};

export type AdminCatalogApiResponse = {
  families: readonly AdminCatalogApiFamily[];
};

type RouteCopy = Pick<
  AdminCatalogViewModelV1,
  "entityLabel" | "filterLabel" | "actionLabel"
>;

const groupCopy: Record<string, RouteCopy> = {
  "用户与数据": {
    entityLabel: "业务记录",
    filterLabel: "筛选用户与数据",
    actionLabel: "处理记录",
  },
  "产品与内容": {
    entityLabel: "产品内容记录",
    filterLabel: "筛选产品与内容",
    actionLabel: "新建版本",
  },
  "排盘与解读": {
    entityLabel: "排盘解读记录",
    filterLabel: "筛选排盘与解读",
    actionLabel: "创建复核任务",
  },
  "商业运营": {
    entityLabel: "商业运营记录",
    filterLabel: "筛选商业运营",
    actionLabel: "处理业务",
  },
  "系统与审计": {
    entityLabel: "系统记录",
    filterLabel: "筛选系统与审计",
    actionLabel: "执行操作",
  },
  总览: {
    entityLabel: "总览记录",
    filterLabel: "筛选总览",
    actionLabel: "执行操作",
  },
  身份: {
    entityLabel: "员工身份",
    filterLabel: "筛选员工身份",
    actionLabel: "执行操作",
  },
};

const actionByPath: Readonly<Record<string, string>> = {
  "/users": "发起密码重置",
  "/data-rights": "处理数据权利请求",
  "/support-cases": "提交补偿申请",
  "/products": "创建商品版本",
  "/capabilities": "变更能力状态",
  "/charts": "创建盘面复核",
  "/reading-jobs": "重试允许的任务",
  "/refunds": "审批退款",
  "/entitlements": "追加权益事件",
  "/referrals": "创建活动版本",
  "/appeals": "处理邀请申诉",
  "/staff": "创建员工",
  "/sessions": "撤销设备会话",
  "/notifications": "重试通知投递",
  "/users/[id]": "发起密码重置",
  "/subjects/[id]": "创建资料更正",
  "/products/[id]/versions": "创建商品版本",
  "/readings/[id]": "创建人工复核",
  "/referrals/[id]": "暂停活动版本",
  "/runtime": "刷新运行时状态",
  "/model-profiles": "创建配置版本",
  "/settings": "保存设置",
  "/health": "重新检查",
};

const columnsByFamily: Readonly<Record<string, readonly AdminCatalogColumnV1[]>> = {
  users: [
    { key: "identity", header: "身份", sortable: true },
    { key: "session", header: "会话" },
    { key: "consent", header: "同意" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  subjects: [
    { key: "subject", header: "Subject", sortable: true },
    { key: "profileVersion", header: "资料版本" },
    { key: "birthBasis", header: "生辰地点" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  requests: [
    { key: "request", header: "请求", sortable: true },
    { key: "category", header: "类型" },
    { key: "subject", header: "相关对象" },
    { key: "deadline", header: "处理期限" },
    { key: "status", header: "状态", sortable: true },
  ],
  content: [
    { key: "content", header: "内容", sortable: true },
    { key: "version", header: "版本" },
    { key: "publishState", header: "发布态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
    { key: "owner", header: "责任人" },
  ],
  capabilities: [
    { key: "capability", header: "能力", sortable: true },
    { key: "capabilityState", header: "能力状态", sortable: true },
    { key: "audience", header: "可用范围" },
    { key: "version", header: "版本" },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  charts: [
    { key: "chart", header: "盘面", sortable: true },
    { key: "subject", header: "受测对象" },
    { key: "viewModel", header: "视图版本" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  readings: [
    { key: "readingRoot", header: "任务根", sortable: true },
    { key: "version", header: "版本" },
    { key: "stage", header: "阶段", sortable: true },
    { key: "subject", header: "受测对象" },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  jobs: [
    { key: "job", header: "任务", sortable: true },
    { key: "readingRoot", header: "任务根" },
    { key: "stage", header: "阶段", sortable: true },
    { key: "retry", header: "重试边界" },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  orders: [
    { key: "order", header: "订单", sortable: true },
    { key: "identity", header: "用户" },
    { key: "amount", header: "金额", sortable: true },
    { key: "fulfillment", header: "交付" },
    { key: "status", header: "状态", sortable: true },
  ],
  payments: [
    { key: "payment", header: "支付尝试", sortable: true },
    { key: "order", header: "订单" },
    { key: "channel", header: "渠道" },
    { key: "settlement", header: "到账事实" },
    { key: "status", header: "状态", sortable: true },
  ],
  refunds: [
    { key: "refund", header: "退款", sortable: true },
    { key: "order", header: "订单" },
    { key: "amount", header: "金额", sortable: true },
    { key: "reason", header: "原因" },
    { key: "status", header: "状态", sortable: true },
  ],
  ledgers: [
    { key: "event", header: "账本事件", sortable: true },
    { key: "account", header: "权益账户" },
    { key: "eventType", header: "事件类型" },
    { key: "source", header: "来源" },
    { key: "status", header: "状态", sortable: true },
  ],
  referrals: [
    { key: "campaign", header: "活动", sortable: true },
    { key: "version", header: "版本" },
    { key: "attribution", header: "归因" },
    { key: "reward", header: "奖励" },
    { key: "status", header: "状态", sortable: true },
  ],
  staff: [
    { key: "staff", header: "员工", sortable: true },
    { key: "role", header: "角色", sortable: true },
    { key: "session", header: "会话" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
  sessions: [
    { key: "session", header: "会话", sortable: true },
    { key: "staff", header: "员工" },
    { key: "device", header: "设备" },
    { key: "lastActive", header: "最近活动", sortable: true },
    { key: "status", header: "状态", sortable: true },
  ],
  audit: [
    { key: "event", header: "审计事件", sortable: true },
    { key: "actor", header: "操作人" },
    { key: "object", header: "影响对象" },
    { key: "result", header: "结果", sortable: true },
    { key: "occurredAt", header: "发生时间", sortable: true },
  ],
  generic: [
    { key: "object", header: "业务对象", sortable: true },
    { key: "scope", header: "作用域" },
    { key: "version", header: "版本" },
    { key: "status", header: "状态", sortable: true },
    { key: "updatedAt", header: "更新时间", sortable: true },
  ],
};

function columnFamilyForRoute(route: AdminRouteDefinition): string {
  if (route.path === "/users") return "users";
  if (route.path === "/subjects") return "subjects";
  if (["/data-rights", "/support-cases", "/appeals"].includes(route.path)) return "requests";
  if (route.path === "/products" || route.path.startsWith("/cms/")) return "content";
  if (route.path === "/capabilities") return "capabilities";
  if (route.path === "/charts" || route.path === "/observations") return "charts";
  if (["/readings", "/verifications"].includes(route.path)) return "readings";
  if (route.path === "/reading-jobs") return "jobs";
  if (route.path === "/orders") return "orders";
  if (route.path === "/payments" || route.path === "/reconciliation") return "payments";
  if (route.path === "/refunds") return "refunds";
  if (route.path === "/entitlements") return "ledgers";
  if (route.path === "/referrals") return "referrals";
  if (route.path === "/staff") return "staff";
  if (route.path === "/sessions") return "sessions";
  if (["/notifications", "/audit"].includes(route.path)) return "audit";
  return "generic";
}

export function getAdminCatalogColumns(
  route: AdminRouteDefinition,
): readonly AdminCatalogColumnV1[] {
  return columnsByFamily[columnFamilyForRoute(route)] ?? columnsByFamily.generic;
}

function copyForRoute(route: AdminRouteDefinition): RouteCopy {
  const group = groupCopy[route.group] ?? groupCopy["系统与审计"];
  return {
    ...group,
    entityLabel: route.label,
    filterLabel: `筛选${route.label}`,
    actionLabel: actionByPath[route.path] ?? group.actionLabel,
  };
}

export function buildLiveAdminCatalogViewModel(
  route: AdminRouteDefinition,
  requestedPath = route.path,
): AdminCatalogViewModelV1 {
  return {
    schema: "admin-catalog/v1",
    source: "live",
    route,
    requestedPath,
    state: "unavailable",
    capabilityState: "UI_PREBUILT",
    ...copyForRoute(route),
    columns: getAdminCatalogColumns(route),
    notice: "真实平台数据与写服务尚未接入；此页不会注入 UI 演示数据。",
    records: [],
  };
}

function productFamilyIdFromPath(pathname: string): string | null {
  const parts = pathname.split("?", 1)[0].split("/").filter(Boolean);
  return parts[1] ?? null;
}

function familyRecord(family: AdminCatalogApiFamily): AdminCatalogRecordV1 {
  return {
    id: family.id,
    primary: family.label,
    secondary: family.key,
    status: family.status,
    updatedAt: family.created_at,
    owner: "Catalog 服务",
    cells: {
      content: family.label,
      version: `${family.versions.length} 个版本`,
      publishState: family.status,
      updatedAt: family.created_at,
      owner: "Catalog 服务",
    },
    details: [
      { label: "商品族 key", value: family.key },
      { label: "版本数量", value: String(family.versions.length) },
      {
        label: "活动版本",
        value: String(family.versions.filter((version) => version.status === "active").length),
      },
    ],
  };
}

function versionRecord(
  family: AdminCatalogApiFamily,
  version: AdminCatalogApiVersion,
): AdminCatalogRecordV1 {
  const enabledOffers = version.offers.filter((offer) => offer.enabled);
  return {
    id: version.id,
    primary: version.version,
    secondary: `${family.label} · ${version.contract_version}`,
    status: version.status,
    updatedAt: version.created_at,
    owner: "Catalog 服务",
    cells: {
      content: family.label,
      version: version.version,
      publishState: version.status,
      updatedAt: version.created_at,
      owner: "Catalog 服务",
    },
    details: [
      { label: "价格", value: `${version.currency} ${version.price_minor}` },
      { label: "交付合同", value: version.contract_version },
      {
        label: "追问额度",
        value: `${version.follow_up_count} 次 · ${version.follow_up_window_seconds} 秒窗口`,
      },
      ...enabledOffers.map((offer) => ({
        label: "启用报价",
        value: `${offer.channel} · ${offer.channel_sku}`,
      })),
    ],
  };
}

export function hydrateLiveProductCatalog(
  model: AdminCatalogViewModelV1,
  payload: AdminCatalogApiResponse,
): AdminCatalogViewModelV1 {
  const isVersionDetail = model.route.path === "/products/[id]/versions";
  const records = isVersionDetail
    ? (() => {
        const family = payload.families.find(
          (candidate) => candidate.id === productFamilyIdFromPath(model.requestedPath),
        );
        return family
          ? family.versions.map((version) => versionRecord(family, version))
          : [];
      })()
    : payload.families.map(familyRecord);
  return {
    ...model,
    state: records.length > 0 ? "ready" : "empty",
    capabilityState: "INTERNAL_TEST",
    notice:
      records.length > 0
        ? "已读取服务端 Catalog；当前界面只读，写操作仍需通过带审计的管理命令。"
        : isVersionDetail
          ? "未找到该商品族的真实版本记录。"
          : "Catalog 当前没有已创建的商品族。",
    records,
  };
}

export function getAdminCatalogCopy(route: AdminRouteDefinition): RouteCopy {
  return copyForRoute(route);
}
