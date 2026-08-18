"use client";

import { useEffect, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type { AdminCapabilitiesResponse } from "@/lib/admin-capabilities";

import styles from "./admin-cms-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "label", header: "能力", sortable: true },
  { key: "releaseState", header: "发布策略", sortable: true },
  { key: "audience", header: "可用范围", sortable: true },
  { key: "actions", header: "产品入口" },
];

const ENVIRONMENT_LABELS: Record<AdminCapabilitiesResponse["environment"], string> = {
  local: "本地",
  test: "测试",
  staging: "预发布",
  production: "生产",
};

const ADAPTER_LABELS: Record<AdminCapabilitiesResponse["runtime_adapter"], string> = {
  fake: "模拟调用",
  "one-shot": "单次真实调用",
};

const RELEASE_STATE_LABELS: Record<string, string> = {
  PUBLIC: "公开",
  INTERNAL_TEST: "内部测试",
};

const ACTION_LABELS: Record<string, string> = {
  profile_preview: "本命格局预览",
  bazi_year_preview: "八字流年预览",
  bazi_month_preview: "八字流月预览",
  bazi_day_preview: "八字流日预览",
  bazi_deep: "八字深度解读",
  five_elements_facts_preview: "五行事实预览",
  chart_similarity_preview: "命盘相似度比较",
  today: "今日运势",
  near_seven: "近七日运势",
  liuyao_one_question: "六爻一事一占",
  liuyao_deep: "六爻深度解读",
  wenshi_one_question: "问事一事一占",
  ziwei_preview: "紫微本命预览",
  ziwei_year_preview: "紫微流年预览",
  ziwei_month_preview: "紫微流月预览",
  qizheng_preview: "七政本命预览",
  qizheng_year_preview: "七政流年预览",
  qizheng_month_preview: "七政流月预览",
  qizheng_day_preview: "七政流日预览",
  canwen_preview: "参问预览",
  hecan_preview: "合参预览",
  bazi_relationship_preview: "八字关系预览",
  ziwei_relationship_preview: "紫微关系预览",
  qizheng_relationship_preview: "七政关系预览",
  meihua_preview: "梅花易数预览",
  luming_nayin_preview: "禄命纳音预览",
  rhythm_preview: "本命音律预览",
  time_check_preview: "寻时定盘预览",
  taiyi_preview: "太乙预览",
  selection_preview: "择日预览",
  fengshui_preview: "风水预览",
  physiognomy_preview: "相法预览",
  qimen_one_question: "奇门一事一占",
  qimen_deep: "奇门深度解读",
  liuren_one_question: "大六壬一事一占",
  liuren_timing_question: "大六壬应期推断",
};

function actionsText(actions: readonly string[]): string {
  return actions.length > 0
    ? actions.map((action) => ACTION_LABELS[action] ?? "未公开产品入口").join("、")
    : "无真实产品入口";
}

export function AdminCapabilitiesSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const [state, setState] = useState<
    "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable"
  >("loading");
  const [data, setData] = useState<AdminCapabilitiesResponse>({
    environment: "local",
    runtime_adapter: "fake",
    runtime_health: "unverified",
    production_ready: false,
    capabilities: [],
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminCapabilitiesResponse>(
        "/api/v1/admin/capabilities?limit=100",
      );
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
      setState(response.data.capabilities.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: TableRow[] = data.capabilities.map((item) => ({
    id: item.capability_id,
    label: item.label,
    releaseState: RELEASE_STATE_LABELS[item.release_state] ?? "未公开发布策略",
    audience: item.audience,
    actions: actionsText(item.product_actions),
  }));

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取能力策略…" description="只读取版本化产品策略，不把静态策略当成运行健康或生产准入。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="能力策略只允许运营或超级管理员读取。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="能力策略平台暂不可用" description="页面不显示虚假的能力发布状态。" />
    ) : state === "error" ? (
      <Status state="error" title="能力策略读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无能力策略" description="注册版本化产品能力策略后，这里会显示真实策略。" />
    ) : (
      <Status state="success" title="能力策略已接入" description="公开只表示产品策略允许展示；运行健康、服务状态和生产准入仍需独立证据。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="capabilities-title">
          <div className={styles.heading}>
            <div>
              <h2 id="capabilities-title">产品能力策略</h2>
              <p>区分对外产品入口与内部服务；不提供未持久化、未审计的能力发布命令。</p>
            </div>
            <span className={styles.badge}>只读策略</span>
          </div>
          <dl className={styles.summary}>
            <div className={styles.summaryItem}>
              <dt>运行环境</dt>
              <dd>{ENVIRONMENT_LABELS[data.environment]}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>运行方式</dt>
              <dd>{ADAPTER_LABELS[data.runtime_adapter]}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>运行时状态</dt>
              <dd>{data.runtime_health === "unverified" ? "未核验" : "未公开状态"}</dd>
            </div>
            <div className={styles.summaryItem}>
              <dt>生产证据</dt>
              <dd>生产准入：{data.production_ready ? "已验证" : "未验证"}</dd>
            </div>
          </dl>
          <Table
            caption="产品能力策略列表"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选能力策略"
            filterPlaceholder="例如：能力、服务、发布策略或产品入口…"
            pageSize={20}
            emptyState="当前没有能力策略"
          />
        </section>
      ) : null}
    </div>
  );
}
