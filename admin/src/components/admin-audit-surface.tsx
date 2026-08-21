"use client";

import { useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminAuditEvent, AdminAuditResponse } from "@/lib/admin-audit";

import styles from "./admin-audit-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "action", header: "动作", sortable: true },
  { key: "actor", header: "操作人", sortable: true },
  { key: "object", header: "对象", sortable: true },
  { key: "result", header: "结果" },
  { key: "createdAt", header: "发生时间", sortable: true },
];

const ACTION_LABELS: Record<string, string> = {
  "physiognomy_media.accepted": "相法媒体已接收",
  "physiognomy_media.deleted": "相法媒体已删除",
  "physiognomy_media.expired": "相法媒体已过期",
  "entitlement.adjusted": "权益已调整",
  "admin.login": "管理员已登录",
  "admin.logout": "管理员已退出",
  "admin.bootstrap_created": "初始管理员已创建",
  "privacy.closure.execute": "隐私关闭已执行",
  "referral.appeal.created": "推荐申诉已创建",
  "referral.appeal.risk_signal.recorded": "推荐申诉风险信号已记录",
  "referral.appeal.decided": "推荐申诉已裁定",
  "referral.appeal.approval.recorded": "推荐申诉批准已记录",
  "referral.appeal.corrected": "推荐申诉已更正",
  "support_case.created": "支持工单已创建",
  "device_session.revoked": "设备会话已撤销",
  "staff.created": "员工已创建",
  "staff.status.updated": "员工状态已更新",
  "staff.role.updated": "员工角色已更新",
  "staff.password.reset": "员工密码已重置",
  "cms.draft.created": "内容草稿已创建",
  "cms.draft.edited": "内容草稿已编辑",
  "cms.revision.previewed": "内容版本已预览",
  "cms.revision.scheduled": "内容版本已排期",
  "cms.revision.published": "内容版本已发布",
  "cms.revision.withdrawn": "内容版本已撤回",
  "cms.revision.archived": "内容版本已归档",
  "cms.revision.restored": "内容版本已恢复",
  "staff.session.revoked": "员工会话已撤销",
  "payment.reconciliation.run": "支付对账已执行",
  "referral.campaign.created": "推荐活动已创建",
  "referral.campaign.state_changed": "推荐活动状态已变更",
  "referral.code.created": "推荐码已创建",
  "referral.reward_slot.created": "推荐奖励位已创建",
  "catalog.family.created": "商品族已创建",
  "catalog.version.created": "商品版本已创建",
  "catalog.offer.created": "商品报价已创建",
  "catalog.version.published": "商品版本已发布",
  "catalog.version.retired": "商品版本已退役",
  "catalog.offer.enabled_changed": "商品报价启用状态已变更",
  "notification.retry": "通知重试已触发",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function objectSummary(event: AdminAuditEvent): string {
  const metadata = event.metadata;
  for (const key of ["target_id", "run_id", "notification_id", "entitlement_id", "family_id"]) {
    const value = metadata[key];
    if (typeof value === "string" && value) return value;
  }
  return "未指定对象";
}

function resultSummary(event: AdminAuditEvent): string {
  const status = event.metadata.status;
  if (status === "success") return "成功";
  if (status === "failed") return "失败";
  if (status === "pending") return "待处理";
  if (event.action.endsWith("retry")) return "已记录重试";
  return "已记录";
}

function rowsFor(events: readonly AdminAuditEvent[]): TableRow[] {
  return events.map((event) => {
    const result = resultSummary(event);
    return {
      id: event.id,
      action: ACTION_LABELS[event.action] ?? "未公开审计动作",
      actor: event.actor,
      object: objectSummary(event),
      result,
      createdAt: formatDate(event.created_at),
      filterCategory:
        result === "失败"
          ? "失败"
          : event.action === "admin.login" || event.action === "admin.logout"
            ? "登录"
            : "写操作",
    };
  });
}

export function AdminAuditSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminAuditResponse>({ events: [] });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminAuditResponse>("/api/v1/admin/audit");
      if (cancelled) return;
      if (!response.ok) {
        setState(
          response.status === 403
            ? "forbidden"
            : response.status === 0 || response.status >= 500
              ? "unavailable"
              : "error",
        );
        setError(response.title);
        return;
      }
      setData(response.data);
      setState(response.data.events.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = useMemo(() => rowsFor(data.events), [data.events]);
  const notice =
    state === "loading" ? (
      <Status compact state="loading" title="正在读取审计日志…" description="只显示服务端允许展示的审计事实。" />
    ) : state === "forbidden" ? (
      <Status compact state="locked" title="无权限" description="全局员工审计只允许超级管理员查看。" />
    ) : state === "unavailable" ? (
      <Status compact state="unavailable" title="审计平台暂不可用" description="页面保留只读结构，不显示假审计结果。" />
    ) : state === "error" ? (
      <Status compact state="error" title="审计日志读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status compact state="empty" title="暂无审计事件" description="管理员成功写入或会话事件产生后，这里会显示可追溯事实。" />
    ) : null;

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" ? (
        <section className={styles.panel} aria-labelledby="audit-list-title">
          <div className={styles.heading}>
            <div>
              <h2 id="audit-list-title">员工审计事件</h2>
              <p>查询动作、操作人、影响对象和结果；详细元数据已由服务端白名单过滤。</p>
            </div>
            <span className={styles.badge}>脱敏读取</span>
          </div>
          <Table
            caption="员工审计事件列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选审计事件"
            filterPlaceholder="例如：动作、操作人或对象…"
            filter={{
              label: "按审计类型或结果筛选",
              rowKey: "filterCategory",
              options: [
                { value: "", label: "全部" },
                { value: "登录", label: "登录" },
                { value: "写操作", label: "写操作" },
                { value: "失败", label: "失败" },
              ],
            }}
            pageSize={20}
            emptyState="没有符合筛选条件的审计事件"
          />
        </section>
      ) : null}
    </div>
  );
}
