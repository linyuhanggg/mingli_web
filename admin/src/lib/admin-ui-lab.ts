import type { StaffRole } from "@/lib/api";
import {
  getAdminCatalogCopy,
  getAdminCatalogColumns,
  type AdminCapabilityState,
  type AdminCatalogRecordV1,
  type AdminCatalogState,
  type AdminCatalogViewModelV1,
  type AdminWriteOperationState,
} from "@/lib/admin-catalog";
import type { AdminRouteDefinition } from "@/lib/admin-route-catalog";
import { ADMIN_ROLE_MATRIX } from "@/lib/admin-permissions";

export {
  ADMIN_PERMISSION_AREAS,
  ADMIN_ROLE_MATRIX,
  type AdminPermissionArea,
  type AdminPermissionLevel,
} from "@/lib/admin-permissions";

export const ADMIN_WRITE_OPERATION_STATES = [
  "无权限",
  "只读",
  "确认",
  "原因",
  "保存中",
  "成功",
  "验证失败",
  "版本冲突",
  "对象已变化",
  "审计完成",
] as const satisfies readonly AdminWriteOperationState[];

export type { AdminWriteOperationState } from "@/lib/admin-catalog";

export const ADMIN_UI_LAB_STATES = [
  "ready",
  "loading",
  "empty",
  "error",
  "forbidden",
  "unavailable",
  "maintenance",
] as const satisfies readonly AdminCatalogState[];

export const ADMIN_CAPABILITY_STATES = [
  "UI_PREBUILT",
  "ADAPTING",
  "INTERNAL_TEST",
  "PUBLIC",
  "PAUSED",
] as const satisfies readonly AdminCapabilityState[];

export type AdminUiLabCatalogViewModel = AdminCatalogViewModelV1 & {
  role: StaffRole;
  writeState: AdminWriteOperationState;
};

const detailByGroup: Readonly<Record<string, readonly { label: string; value: string }[]>> = {
  "用户与数据": [
    { label: "姓名", value: "林青（演示）" },
    { label: "工作联系", value: "qing.lin@example.test · 138 0000 0001" },
    { label: "出生地点", value: "江苏省常州市（演示）" },
    { label: "资料版本", value: "ProfileVersion v3" },
  ],
  "产品与内容": [
    { label: "内容版本", value: "v5（演示）" },
    { label: "发布范围", value: "仅内部测试" },
    { label: "编辑人", value: "运营演示账号" },
    { label: "审核", value: "等待复核" },
  ],
  "排盘与解读": [
    { label: "受测对象", value: "林青（演示）" },
    { label: "盘面版本", value: "Chart Snapshot v2" },
    { label: "解读版本", value: "Reading Version v1" },
    { label: "当前阶段", value: "等待人工复核" },
  ],
  商业运营: [
    { label: "订单", value: "ORD-DEMO-20260813-01" },
    { label: "展示金额", value: "¥99.00（演示）" },
    { label: "支付事实", value: "等待服务端确认" },
    { label: "权益事件", value: "尚未写入" },
  ],
  "系统与审计": [
    { label: "环境", value: "测试环境" },
    { label: "操作员工", value: "演示员工" },
    { label: "审计结果", value: "等待写入" },
    { label: "敏感信息", value: "不在界面展示" },
  ],
};

function fixtureCellValue(
  key: string,
  index: number,
  role: StaffRole,
  capabilityState: AdminCapabilityState,
): string {
  const suffix = index === 0 ? "001" : "002";
  const values: Readonly<Record<string, readonly [string, string]>> = {
    identity: ["林青（演示）", "周岚（演示）"],
    contact: ["qing.lin@example.test", "lan.zhou@example.test"],
    session: ["1 个有效会话", "无有效会话"],
    consent: ["政策 v3 · 已记录", "政策 v2 · 待更新"],
    subject: ["林青（演示）", "周岚（演示）"],
    profileVersion: ["ProfileVersion v3", "ProfileVersion v1"],
    birthBasis: ["江苏常州（演示）", "广东广州（演示）"],
    request: [`REQ-DEMO-${suffix}`, `REQ-DEMO-${suffix}`],
    category: ["资料纠正 / 补偿申请", "售后复核"],
    deadline: ["2026-08-16 18:00", "2026-08-18 18:00"],
    content: ["首页运营文案（演示）", "帮助中心条目（演示）"],
    version: ["v5（演示）", "v4（演示）"],
    publishState: ["仅内部测试", "草稿"],
    capability: ["reading-generation（演示）", "chart-adapter（演示）"],
    capabilityState: [capabilityState, capabilityState],
    audience: ["测试员工", "测试账号"],
    chart: [`CHART-DEMO-${suffix}`, `CHART-DEMO-${suffix}`],
    viewModel: ["chart-view/v2", "chart-view/v1"],
    readingRoot: [`ROOT-DEMO-${suffix}`, `ROOT-DEMO-${suffix}`],
    stage: ["等待人工复核", "已交付 · 只读"],
    job: [`JOB-DEMO-${suffix}`, `JOB-DEMO-${suffix}`],
    retry: ["允许人工重试", "终态不可重试"],
    order: [`ORD-DEMO-20260813-${suffix}`, `ORD-DEMO-20260812-${suffix}`],
    amount: ["¥99.00（演示）", "¥199.00（演示）"],
    fulfillment: ["等待服务端事实", "已交付（演示）"],
    payment: [`PAY-DEMO-${suffix}`, `PAY-DEMO-${suffix}`],
    channel: ["测试支付渠道", "测试支付渠道"],
    settlement: ["等待服务端确认", "已核对（演示）"],
    refund: [`REF-DEMO-${suffix}`, `REF-DEMO-${suffix}`],
    reason: ["用户申请（演示）", "售后复核（演示）"],
    event: [`EVENT-DEMO-${suffix}`, `EVENT-DEMO-${suffix}`],
    account: [`ENT-DEMO-${suffix}`, `ENT-DEMO-${suffix}`],
    eventType: ["RESERVE（演示）", "RELEASE（演示）"],
    source: ["显式 Fixture", "显式 Fixture"],
    campaign: ["邀请活动（演示）", "历史活动（演示）"],
    attribution: ["等待有效归因", "归因已结束"],
    reward: ["尚未产生", "已冲正（演示）"],
    staff: ["演示员工甲", "演示员工乙"],
    role: [role, index === 0 ? role : "support"],
    device: ["Chrome · 测试设备", "Safari · 测试设备"],
    lastActive: ["2026-08-13 14:20", "2026-08-12 09:45"],
    actor: ["演示员工甲", "演示员工乙"],
    object: [`业务对象 DEMO-${suffix}`, `业务对象 DEMO-${suffix}`],
    result: ["等待审计", "只读"],
    occurredAt: ["2026-08-13 14:20", "2026-08-12 09:45"],
    scope: ["测试环境", "UI Lab"],
    status: [capabilityState === "PAUSED" ? "已暂停" : "待处理", "只读"],
    updatedAt: ["2026-08-13 14:20", "2026-08-12 09:45"],
    owner: ["运营演示账号", "系统演示"],
  };
  return values[key]?.[index] ?? `${key} · DEMO-${suffix}`;
}

function fixtureCells(
  route: AdminRouteDefinition,
  index: number,
  role: StaffRole,
  capabilityState: AdminCapabilityState,
): Readonly<Record<string, string>> {
  return Object.fromEntries(
    getAdminCatalogColumns(route).map((column) => [
      column.key,
      fixtureCellValue(column.key, index, role, capabilityState),
    ]),
  );
}

function fixtureRecords(
  route: AdminRouteDefinition,
  role: StaffRole,
  capabilityState: AdminCapabilityState,
): readonly AdminCatalogRecordV1[] {
  const details = detailByGroup[route.group] ?? detailByGroup["系统与审计"];
  return [
    {
      id: `${route.label}-DEMO-001`,
      primary: `${route.label}演示记录`,
      secondary: "用于验收列表、筛选、详情与写操作，不代表真实业务事实。",
      status: capabilityState === "PAUSED" ? "已暂停" : "待处理",
      updatedAt: "2026-08-13 14:20",
      owner: ADMIN_ROLE_MATRIX.find((item) => item.role === role)?.label ?? role,
      cells: fixtureCells(route, 0, role, capabilityState),
      details: [
        ...details,
        { label: "当前角色", value: role },
        { label: "能力状态", value: capabilityState },
      ],
    },
    {
      id: `${route.label}-DEMO-002`,
      primary: `${route.label}只读样例`,
      secondary: "第二条演示记录用于检查排序、选择与分页密度。",
      status: "只读",
      updatedAt: "2026-08-12 09:45",
      owner: "系统演示",
      cells: fixtureCells(route, 1, role, capabilityState),
      details: [
        { label: "记录用途", value: "UI Lab 响应式与可访问性验收" },
        { label: "数据来源", value: "显式 Fixture" },
        { label: "能力状态", value: capabilityState },
      ],
    },
  ];
}

export function buildAdminUiLabCatalogViewModel(
  route: AdminRouteDefinition,
  options: {
    state: AdminCatalogState;
    role: StaffRole;
    capabilityState: AdminCapabilityState;
    writeState: AdminWriteOperationState;
  },
): AdminUiLabCatalogViewModel {
  return {
    schema: "admin-catalog/v1",
    source: "fixture",
    route,
    requestedPath: route.path,
    state: options.state,
    capabilityState: options.capabilityState,
    ...getAdminCatalogCopy(route),
    columns: getAdminCatalogColumns(route),
    notice: "UI 演示数据：所有姓名、编号、金额、状态和审计结果均为显式 Fixture。",
    records:
      options.state === "ready"
        ? fixtureRecords(route, options.role, options.capabilityState)
        : [],
    role: options.role,
    writeState: options.writeState,
  };
}

export const ADMIN_WRITE_OPERATION_STATE_COPY: Record<AdminWriteOperationState, string> = {
  "无权限": "当前角色不能执行这项写操作。",
  "只读": "可以查看事实，但不能直接改动对象。",
  "确认": "提交前展示对象、范围和影响，要求主动确认。",
  "原因": "补偿、重试或撤回必须填写可审计原因。",
  "保存中": "请求进行中，按钮锁定，不能重复提交。",
  "成功": "服务端已接受写入，页面显示新的事实状态。",
  "验证失败": "服务端校验未通过，保留输入并明确失败原因。",
  "版本冲突": "对象版本已变化，要求重新读取后再提交。",
  "对象已变化": "目标对象已被处理或关闭，当前操作不可继续。",
  "审计完成": "写入与操作者、原因、对象和时间已形成审计记录。",
};
