"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import {
  Button,
  Dialog,
  Drawer,
  Status,
  Table,
  type TableColumn,
  type TableRow,
} from "@/components/ui";
import { useAdminStaff } from "@/components/admin-shell";
import { AdminCatalogCommands } from "@/components/admin-catalog-commands";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminCatalogApiResponse,
  AdminCatalogRecordV1,
  AdminCatalogViewModelV1,
  AdminWriteOperationState,
} from "@/lib/admin-catalog";
import { hydrateLiveProductCatalog } from "@/lib/admin-catalog";
import { getAdminPermissionArea, getAdminRouteAccess } from "@/lib/admin-permissions";
import { ADMIN_WRITE_OPERATION_STATE_COPY } from "@/lib/admin-ui-lab";

import styles from "./admin-catalog-surface.module.css";

function toTableRows(model: AdminCatalogViewModelV1): TableRow[] {
  return model.records.map((record) => ({
    id: record.id,
    ...record.cells,
  }));
}

function surfaceName(model: AdminCatalogViewModelV1): string {
  switch (model.route.surface) {
    case "detail":
      return "详情";
    case "operations":
      return "操作面";
    case "health":
      return "健康检查";
    case "settings":
      return "设置";
    case "list":
    default:
      return "列表";
  }
}

function StateNotice({ model }: { model: AdminCatalogViewModelV1 }) {
  const noun = surfaceName(model);
  switch (model.state) {
    case "ready":
      return null;
    case "loading":
      return <Status state="loading" title={`正在读取${noun}…`} description={model.notice} />;
    case "empty":
      return <Status state="empty" title={`当前${noun}没有记录`} description={model.notice} />;
    case "error":
      return <Status state="error" title={`${noun}读取失败`} description="请求失败；请重试或检查平台服务。" />;
    case "forbidden":
      return <Status state="locked" title="无权限" description="服务端拒绝当前角色访问此业务页面。" />;
    case "maintenance":
      return <Status state="unavailable" title="维护中" description="当前页面暂时停止新操作，历史记录仍保留。" />;
    case "unavailable":
    default:
      return <Status state="unavailable" title="平台数据暂时不可用。" description={model.notice} />;
  }
}

function DetailContent({ record }: { record: AdminCatalogRecordV1 }) {
  return (
    <div className={styles.detailStack}>
      <div className={styles.detailSummary}>
        <span>{record.status}</span>
        <p>{record.secondary}</p>
      </div>
      <dl className={styles.details}>
        <div>
          <dt>记录编号</dt>
          <dd>{record.id}</dd>
        </div>
        {record.details.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
        <div>
          <dt>最后更新</dt>
          <dd>{record.updatedAt}</dd>
        </div>
      </dl>
      <p className={styles.detailFootnote}>完整业务资料按当前员工角色展示；系统秘密永不进入此详情。</p>
    </div>
  );
}

function SurfaceHeading({
  id,
  title,
  description,
  capabilityState,
}: {
  id: string;
  title: string;
  description: string;
  capabilityState: string;
}) {
  return (
    <div className={styles.sectionHeading}>
      <div>
        <h2 id={id}>{title}</h2>
        <p>{description}</p>
      </div>
      <span className={styles.capability}>{capabilityState}</span>
    </div>
  );
}

function getRequestedObjectId(model: AdminCatalogViewModelV1): string {
  const pattern = model.route.path.split("/").filter(Boolean);
  const requested = model.requestedPath.split("?")[0].split("/").filter(Boolean);
  const dynamicIndex = pattern.findIndex((part) => part.startsWith("["));
  if (dynamicIndex < 0) return model.route.label;
  const value = requested[dynamicIndex];
  return value && !value.startsWith("[") ? value : "待平台解析";
}

function DetailSurface({ model }: { model: AdminCatalogViewModelV1 }) {
  const record = model.records[0];
  return (
    <section className={styles.listSection} aria-labelledby="catalog-detail-title">
      <SurfaceHeading
        id="catalog-detail-title"
        title={`${model.route.label}字段`}
        description="详情页按对象、版本与审计事实组织，不复用列表列定义。"
        capabilityState={model.capabilityState}
      />
      {record ? (
        <DetailContent record={record} />
      ) : (
        <dl className={styles.details}>
          <div>
            <dt>对象标识</dt>
            <dd>{getRequestedObjectId(model)}</dd>
          </div>
          <div>
            <dt>页面结构</dt>
            <dd>详情字段、版本记录与审计入口</dd>
          </div>
          <div>
            <dt>数据状态</dt>
            <dd>真实详情服务尚未接入</dd>
          </div>
          <div>
            <dt>权限区</dt>
            <dd>{getAdminPermissionArea(model.route)}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}

function OperationsSurface({ model }: { model: AdminCatalogViewModelV1 }) {
  const title = model.route.path === "/runtime" ? "运行时控制面" : `${model.route.label}操作面`;
  return (
    <section className={styles.listSection} aria-labelledby="catalog-operations-title">
      <SurfaceHeading
        id="catalog-operations-title"
        title={title}
        description="操作面展示连接状态、变更边界与审计入口，不伪装成业务记录列表。"
        capabilityState={model.capabilityState}
      />
      <dl className={styles.details}>
        <div>
          <dt>数据通道</dt>
          <dd>{model.source === "fixture" ? "UI 演示数据" : "当前没有可展示的连接状态。"}</dd>
        </div>
        <div>
          <dt>能力状态</dt>
          <dd>{model.capabilityState}</dd>
        </div>
        <div>
          <dt>服务端边界</dt>
          <dd>读取状态与写入命令必须由服务端重新校验权限</dd>
        </div>
        <div>
          <dt>权限区</dt>
          <dd>{getAdminPermissionArea(model.route)}</dd>
        </div>
      </dl>
    </section>
  );
}

function HealthSurface({ model }: { model: AdminCatalogViewModelV1 }) {
  return (
    <section className={styles.listSection} aria-labelledby="catalog-health-title">
      <SurfaceHeading
        id="catalog-health-title"
        title="健康检查面"
        description="只呈现已返回的检查事实；未接入时不显示虚假的正常指标。"
        capabilityState={model.capabilityState}
      />
      <dl className={styles.details}>
        <div>
          <dt>检查来源</dt>
          <dd>{model.source === "fixture" ? "UI 演示数据" : "当前没有可展示的检查结果。"}</dd>
        </div>
        <div>
          <dt>检查范围</dt>
          <dd>任务队列与依赖服务</dd>
        </div>
        <div>
          <dt>当前结论</dt>
          <dd>{model.source === "fixture" ? "仅验证状态布局" : "暂无可核验的实时结论"}</dd>
        </div>
      </dl>
    </section>
  );
}

function SettingsSurface({ model }: { model: AdminCatalogViewModelV1 }) {
  return (
    <section className={styles.listSection} aria-labelledby="catalog-settings-title">
      <SurfaceHeading
        id="catalog-settings-title"
        title="系统设置面"
        description="配置按版本和作用域展示，保存前必须明确差异与审计原因。"
        capabilityState={model.capabilityState}
      />
      <dl className={styles.details}>
        <div>
          <dt>配置来源</dt>
          <dd>{model.source === "fixture" ? "UI 演示数据" : "真实配置服务尚未接入"}</dd>
        </div>
        <div>
          <dt>版本策略</dt>
          <dd>新配置生成新版本，不覆盖已生效审计记录</dd>
        </div>
        <div>
          <dt>保存边界</dt>
          <dd>服务端权限、校验、冲突与审计全部成功后才生效</dd>
        </div>
      </dl>
    </section>
  );
}

export function AdminCatalogSurface({
  model: initialModel,
  role,
  writeState,
}: {
  model: AdminCatalogViewModelV1;
  role?: StaffRole;
  writeState?: AdminWriteOperationState;
}) {
  const isProductCatalogRoute =
    initialModel.source === "live" &&
    ["/products", "/products/[id]/versions"].includes(initialModel.route.path);
  const [liveModel, setLiveModel] = useState(() =>
    isProductCatalogRoute
      ? {
          ...initialModel,
          state: "loading" as const,
          notice: "正在读取服务端 Catalog…",
        }
      : initialModel,
  );
  const [livePayload, setLivePayload] = useState<AdminCatalogApiResponse | null>(null);

  const loadLiveCatalog = useCallback(
    async (isCancelled?: () => boolean): Promise<boolean> => {
      const result = await adminFetch<AdminCatalogApiResponse>("/api/v1/admin/catalog");
      if (isCancelled?.()) return false;
      if (result.ok) {
        setLivePayload(result.data);
        setLiveModel(hydrateLiveProductCatalog(initialModel, result.data));
        return true;
      }
      const state: AdminCatalogViewModelV1["state"] =
        result.status === 403
          ? "forbidden"
          : result.status === 0 || result.status >= 500
            ? "unavailable"
            : "error";
      setLiveModel({ ...initialModel, state, notice: result.title });
      return false;
    },
    [initialModel],
  );

  useEffect(() => {
    if (!isProductCatalogRoute) return;
    let cancelled = false;
    void (async () => {
      const result = await adminFetch<AdminCatalogApiResponse>("/api/v1/admin/catalog");
      if (cancelled) return;
      if (result.ok) {
        setLivePayload(result.data);
        setLiveModel(hydrateLiveProductCatalog(initialModel, result.data));
        return;
      }
      const state: AdminCatalogViewModelV1["state"] =
        result.status === 403
          ? "forbidden"
          : result.status === 0 || result.status >= 500
            ? "unavailable"
            : "error";
      setLiveModel({ ...initialModel, state, notice: result.title });
    })();
    return () => {
      cancelled = true;
    };
  }, [initialModel, isProductCatalogRoute]);

  const model = liveModel;
  const rows = toTableRows(model);
  const [selectedIds, setSelectedIds] = useState<readonly string[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<AdminCatalogRecordV1 | null>(null);
  const [writeOpen, setWriteOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [writeResult, setWriteResult] = useState<AdminWriteOperationState | null>(null);
  const detailTriggerRef = useRef<HTMLElement | null>(null);
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const configuredWriteState = writeState ?? (model.source === "fixture" ? "确认" : "只读");
  const access = effectiveRole
    ? getAdminRouteAccess(effectiveRole, model.route, model.capabilityState)
    : { area: getAdminPermissionArea(model.route), read: "禁止" as const, write: "禁止" as const };
  const roleAllowsWrite = access.write === "允许" || access.write === "提交申请";
  const effectiveWriteState = writeResult ?? configuredWriteState;
  const blockedByState = configuredWriteState === "无权限" || configuredWriteState === "只读";
  const requiresSelection = model.route.surface === "list";
  const hasWriteTarget = !requiresSelection || selectedIds.length > 0;
  const writeDisabled =
    !roleAllowsWrite ||
    blockedByState ||
    model.state !== "ready" ||
    !hasWriteTarget;
  const writeReason =
    model.source !== "fixture"
      ? isProductCatalogRoute
        ? "服务端 Catalog 读取与带审计写命令已接入；当前页面写表单尚未接入，控件保持只读。"
        : "当前不能写入；控件保持只读。"
      : !roleAllowsWrite || configuredWriteState === "无权限"
        ? "当前角色不能执行此写操作；按钮保持可见，由服务端继续拒绝。"
        : configuredWriteState === "只读"
          ? "当前演示状态为只读；查看不等于授权修改。"
          : requiresSelection && selectedIds.length === 0
            ? "请先选择一个或多个影响对象；确认弹层会逐项列出本次范围。"
            : ADMIN_WRITE_OPERATION_STATE_COPY[configuredWriteState];
  const selectedRecords = selectedIds
    .map((id) => model.records.find((record) => record.id === id))
    .filter((record): record is AdminCatalogRecordV1 => Boolean(record));
  const writeTarget =
    model.route.surface === "list"
      ? selectedRecords.length > 1
        ? `已选择 ${selectedRecords.length} 项：${selectedRecords.map((record) => record.primary).join("、")}`
        : selectedRecords[0]?.primary ?? "尚未选择对象"
      : model.route.surface === "detail"
        ? model.records[0]?.primary ?? `${model.route.label} · ${getRequestedObjectId(model)}`
        : `${model.route.label}操作面`;
  const showLiveCatalogCommands =
    isProductCatalogRoute &&
    livePayload !== null &&
    effectiveRole !== undefined &&
    roleAllowsWrite &&
    (model.state === "ready" || model.state === "empty");

  function openDetail(row: TableRow) {
    if (document.activeElement instanceof HTMLElement) {
      detailTriggerRef.current = document.activeElement;
    }
    setSelectedRecord(model.records.find((record) => record.id === row.id) ?? null);
  }

  function submitDemoWrite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (reason.trim().length < 4) {
      setReasonError("请填写至少 4 个字的操作原因。");
      return;
    }
    setReasonError(null);
    setWriteResult("审计完成");
  }

  return (
    <div
      className={styles.stack}
      data-source={model.source}
      data-staff-role={effectiveRole ?? "session"}
      data-route-surface={model.route.surface}
    >
      <StateNotice model={model} />

      {model.route.surface === "list" ? (
        <section className={styles.listSection} aria-labelledby="catalog-list-title">
          <SurfaceHeading
            id="catalog-list-title"
            title={`${model.entityLabel}列表`}
            description="筛选、排序、分页、批量选择与详情入口按正式页面结构保留。"
            capabilityState={model.capabilityState}
          />
          <Table
            caption={`${model.entityLabel}列表`}
            columns={model.columns.map((column): TableColumn => ({ ...column }))}
            rows={rows}
            filterLabel={model.filterLabel}
            filterPlaceholder="例如：编号、名称或状态…"
            selectable
            onSelectionChange={setSelectedIds}
            pageSize={10}
            emptyState={model.source === "live" ? "没有可显示的真实记录" : "此演示状态没有记录"}
            onRowActivate={rows.length > 0 ? openDetail : undefined}
            rowActionLabel="查看详情"
          />
        </section>
      ) : model.route.surface === "detail" ? (
        <DetailSurface model={model} />
      ) : model.route.surface === "operations" ? (
        <OperationsSurface model={model} />
      ) : model.route.surface === "health" ? (
        <HealthSurface model={model} />
      ) : (
        <SettingsSurface model={model} />
      )}

      <Drawer
        open={selectedRecord !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedRecord(null);
        }}
        side="right"
        title={selectedRecord ? `${selectedRecord.primary}详情` : `${model.entityLabel}详情`}
        description="查看完整业务字段与版本状态。"
        restoreFocusRef={detailTriggerRef}
      >
        {selectedRecord ? <DetailContent record={selectedRecord} /> : null}
      </Drawer>

      {showLiveCatalogCommands ? (
        <AdminCatalogCommands
          payload={livePayload}
          pathname={initialModel.requestedPath}
          role={effectiveRole!}
          onRefresh={loadLiveCatalog}
        />
      ) : (
        <section className={styles.writeSection} aria-labelledby="catalog-write-title">
          <div>
            <h2 id="catalog-write-title">写操作</h2>
            <p id="catalog-write-permission">
              权限边界：{access.area} · 查看“{access.read}” · 写入“{access.write}”
            </p>
            <p id="catalog-write-reason">{writeReason}</p>
          </div>
          <Dialog
            open={writeOpen}
            onOpenChange={(open) => {
              setWriteOpen(open);
              if (!open) {
                setReason("");
                setReasonError(null);
                setWriteResult(null);
              }
            }}
            title={`确认${model.actionLabel}`}
            description="写操作必须说明影响对象与原因，并留下审计结果。"
            trigger={
              <Button
                type="button"
                disabled={writeDisabled}
                aria-describedby="catalog-write-permission catalog-write-reason"
              >
                {model.actionLabel}
              </Button>
            }
          >
            <div className={styles.writeDialog}>
              <dl className={styles.impactSummary}>
                <div>
                  <dt>影响对象</dt>
                  <dd>{writeTarget}</dd>
                </div>
                <div>
                  <dt>当前角色</dt>
                  <dd>{effectiveRole ?? "会话角色"}</dd>
                </div>
                <div>
                  <dt>路由权限</dt>
                  <dd>{access.area} · 查看 {access.read} · 写入 {access.write}</dd>
                </div>
                <div>
                  <dt>演示状态</dt>
                  <dd>{effectiveWriteState}</dd>
                </div>
              </dl>

              {effectiveWriteState === "确认" ? (
                <div className={styles.reasonForm}>
                  <p>{ADMIN_WRITE_OPERATION_STATE_COPY.确认}</p>
                  <Button type="button" onClick={() => setWriteResult("成功")}>
                    确认并提交
                  </Button>
                </div>
              ) : effectiveWriteState === "成功" ? (
                <Status state="success" title="写操作已成功" description="演示结果已返回，尚待审计记录。" />
              ) : effectiveWriteState === "审计完成" ? (
                <Status state="success" title="审计记录已完成" description="演示写操作与原因已经关联。" />
              ) : effectiveWriteState === "版本冲突" ? (
                <Status state="error" title="版本冲突" description="对象版本已变化；刷新后重新确认，不能覆盖新版本。" />
              ) : effectiveWriteState === "对象已变化" ? (
                <Status state="locked" title="对象已变化" description="影响对象不再符合原条件；本次操作未执行。" />
              ) : (
                <form className={styles.reasonForm} onSubmit={submitDemoWrite}>
                  {effectiveWriteState === "验证失败" ? (
                    <p className={styles.inlineAlert} role="alert">验证失败：原因与影响对象不匹配。</p>
                  ) : null}
                  <label htmlFor="admin-write-reason">操作原因</label>
                  <textarea
                    id="admin-write-reason"
                    name="reason"
                    autoComplete="off"
                    required
                    aria-invalid={reasonError ? "true" : undefined}
                    aria-describedby={reasonError ? "admin-write-reason-error" : "admin-write-reason-help"}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                  />
                  <p id="admin-write-reason-help">原因会与影响对象、角色和结果一起进入审计。</p>
                  {reasonError ? (
                    <p id="admin-write-reason-error" className={styles.inlineAlert} role="alert">
                      {reasonError}
                    </p>
                  ) : null}
                  <Button type="submit" loading={effectiveWriteState === "保存中"}>
                    确认并记录审计
                  </Button>
                </form>
              )}
            </div>
          </Dialog>
        </section>
      )}
    </div>
  );
}
