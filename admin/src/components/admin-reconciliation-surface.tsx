"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Drawer, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminReconciliationPaymentDraft,
  AdminReconciliationRefundDraft,
  AdminReconciliationResponse,
  AdminReconciliationRun,
} from "@/lib/admin-reconciliation";

import styles from "./admin-reconciliation-surface.module.css";

const RUN_COLUMNS: TableColumn[] = [
  { key: "channel", header: "渠道", sortable: true },
  { key: "runAt", header: "批次时间", sortable: true },
  { key: "status", header: "结果", sortable: true },
  { key: "itemCount", header: "条目数", sortable: true },
  { key: "differenceCount", header: "差异数", sortable: true },
];

const OPERATOR_ROLES: ReadonlySet<StaffRole> = new Set(["finance", "ops", "superadmin"]);

const EMPTY_PAYMENT: AdminReconciliationPaymentDraft = {
  transaction_id: "",
  status: "succeeded",
  amount_minor: "0",
  currency: "CNY",
};

const EMPTY_REFUND: AdminReconciliationRefundDraft = {
  refund_id: "",
  payment_transaction_id: "",
  status: "succeeded",
  amount_minor: "0",
  currency: "CNY",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function runRows(runs: readonly AdminReconciliationRun[]): TableRow[] {
  return runs.map((run) => ({
    id: run.id,
    channel: run.channel,
    runAt: formatDate(run.run_at),
    status: run.status === "matched" ? "已匹配" : "有差异",
    itemCount: run.item_count,
    differenceCount: run.difference_count,
  }));
}

export function AdminReconciliationSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const canOperate = effectiveRole !== undefined && OPERATOR_ROLES.has(effectiveRole);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable">("loading");
  const [data, setData] = useState<AdminReconciliationResponse>({ runs: [] });
  const [selectedRun, setSelectedRun] = useState<AdminReconciliationRun | null>(null);
  const [channel, setChannel] = useState("closed");
  const [reason, setReason] = useState("");
  const [payments, setPayments] = useState<AdminReconciliationPaymentDraft[]>([EMPTY_PAYMENT]);
  const [refunds, setRefunds] = useState<AdminReconciliationRefundDraft[]>([]);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    const response = await adminFetch<AdminReconciliationResponse>("/api/v1/admin/reconciliation");
    if (!response.ok) {
      setState(
        response.status === 403
          ? "forbidden"
          : response.status === 0 || response.status >= 500
            ? "unavailable"
            : "error",
      );
      setError(response.title);
      return false;
    }
    setData(response.data);
    setState(response.data.runs.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminReconciliationResponse>("/api/v1/admin/reconciliation");
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
      setState(response.data.runs.length > 0 ? "ready" : "empty");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = useMemo(() => runRows(data.runs), [data.runs]);

  function updatePayment(index: number, field: keyof AdminReconciliationPaymentDraft, value: string) {
    setPayments((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
  }

  function updateRefund(index: number, field: keyof AdminReconciliationRefundDraft, value: string) {
    setRefunds((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
  }

  async function submitRun() {
    const normalizedReason = reason.trim();
    const activePayments = payments.filter((item) => item.transaction_id.trim());
    const activeRefunds = refunds.filter((item) => item.refund_id.trim());
    if (!channel.trim() || normalizedReason.length < 4) {
      setError("请填写渠道和至少 4 个字的对账原因。");
      return;
    }
    setPending(true);
    setError(null);
    setResult(null);
    const response = await adminFetch<AdminReconciliationRun>("/api/v1/admin/reconciliation/runs", {
      method: "POST",
      body: JSON.stringify({
        channel: channel.trim(),
        reason: normalizedReason,
        payments: activePayments.map((item) => ({
          ...item,
          transaction_id: item.transaction_id.trim(),
          amount_minor: Number(item.amount_minor),
          currency: item.currency.trim().toUpperCase(),
        })),
        refunds: activeRefunds.map((item) => ({
          ...item,
          refund_id: item.refund_id.trim(),
          payment_transaction_id: item.payment_transaction_id.trim() || null,
          amount_minor: Number(item.amount_minor),
          currency: item.currency.trim().toUpperCase(),
        })),
      }),
    });
    if (!response.ok) {
      setError(response.title);
      setPending(false);
      return;
    }
    const refreshed = await loadRuns();
    setResult(refreshed ? "对账批次已完成，差异事实已保存。" : "对账批次已保存，但列表刷新失败；请重新读取。");
    setPending(false);
  }

  function openRun(row: TableRow) {
    setSelectedRun(data.runs.find((run) => run.id === row.id) ?? null);
  }

  const stateNotice =
    state === "loading" ? (
      <Status state="loading" title="正在读取对账批次…" description="只显示服务端已经保存的对账事实。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="对账只允许财务、运营或超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="对账平台暂不可用" description="页面保留只读结构，不显示假差异或假金额。" />
    ) : state === "error" ? (
      <Status state="error" title="对账读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无对账批次" description="完成一次已验签快照对账后，这里会显示批次和差异。" />
    ) : (
      <Status state="success" title="对账事实已接入" description="列表只展示服务端批次；差异详情可逐批查看。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {stateNotice}
      {result ? <Status state="success" title={result} description="本次命令已通过服务端权限、CSRF 和审计边界。" /> : null}
      <section className={styles.panel} aria-labelledby="reconciliation-list-title">
        <div className={styles.heading}>
          <div>
            <h2 id="reconciliation-list-title">对账批次</h2>
            <p>按渠道和批次读取 Payment/Refund 本地事实与已验签渠道快照的差异。</p>
          </div>
          <span className={styles.badge}>真实数据</span>
        </div>
        <Table
          caption="对账批次列表"
          columns={RUN_COLUMNS}
          rows={rows}
          filterLabel="筛选对账批次"
          filterPlaceholder="例如：渠道、状态或批次编号…"
          pageSize={10}
          emptyState="当前没有已保存的对账批次"
          onRowActivate={rows.length > 0 ? openRun : undefined}
          rowActionLabel="查看差异"
        />
      </section>

      {canOperate ? (
        <section className={styles.panel} aria-labelledby="reconciliation-command-title">
          <div className={styles.heading}>
            <div>
              <h2 id="reconciliation-command-title">执行对账</h2>
              <p>仅提交已由渠道适配器验签、归一化的快照；本页不执行第三方渠道验签。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <div className={styles.formGrid}>
            <label>
              渠道
              <input value={channel} onChange={(event) => setChannel(event.target.value)} required />
            </label>
            <label className={styles.wideField}>
              操作原因
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                minLength={4}
                required
                placeholder="说明本次对账的来源和业务原因…"
              />
            </label>
          </div>

          <fieldset className={styles.snapshotGroup}>
            <legend>支付快照</legend>
            {payments.map((item, index) => (
              <div className={styles.snapshotRow} key={`payment-${index}`}>
                <label>
                  交易号
                  <input value={item.transaction_id} onChange={(event) => updatePayment(index, "transaction_id", event.target.value)} />
                </label>
                <label>
                  状态
                  <select value={item.status} onChange={(event) => updatePayment(index, "status", event.target.value)}>
                    <option value="pending">pending</option>
                    <option value="succeeded">succeeded</option>
                    <option value="failed">failed</option>
                    <option value="refunded">refunded</option>
                  </select>
                </label>
                <label>
                  金额（分）
                  <input type="number" min={0} value={item.amount_minor} onChange={(event) => updatePayment(index, "amount_minor", event.target.value)} />
                </label>
                <label>
                  币种
                  <input maxLength={3} value={item.currency} onChange={(event) => updatePayment(index, "currency", event.target.value)} />
                </label>
                <Button variant="ghost" type="button" onClick={() => setPayments((current) => current.filter((_, itemIndex) => itemIndex !== index))} disabled={payments.length === 1}>
                  移除
                </Button>
              </div>
            ))}
            <Button variant="secondary" type="button" onClick={() => setPayments((current) => [...current, { ...EMPTY_PAYMENT }])}>
              添加支付快照
            </Button>
          </fieldset>

          <fieldset className={styles.snapshotGroup}>
            <legend>退款快照</legend>
            {refunds.map((item, index) => (
              <div className={styles.snapshotRow} key={`refund-${index}`}>
                <label>
                  退款号
                  <input value={item.refund_id} onChange={(event) => updateRefund(index, "refund_id", event.target.value)} />
                </label>
                <label>
                  支付交易号
                  <input value={item.payment_transaction_id} onChange={(event) => updateRefund(index, "payment_transaction_id", event.target.value)} />
                </label>
                <label>
                  状态
                  <select value={item.status} onChange={(event) => updateRefund(index, "status", event.target.value)}>
                    <option value="pending">pending</option>
                    <option value="succeeded">succeeded</option>
                    <option value="failed">failed</option>
                  </select>
                </label>
                <label>
                  金额（分）
                  <input type="number" min={0} value={item.amount_minor} onChange={(event) => updateRefund(index, "amount_minor", event.target.value)} />
                </label>
                <label>
                  币种
                  <input maxLength={3} value={item.currency} onChange={(event) => updateRefund(index, "currency", event.target.value)} />
                </label>
                <Button variant="ghost" type="button" onClick={() => setRefunds((current) => current.filter((_, itemIndex) => itemIndex !== index))}>
                  移除
                </Button>
              </div>
            ))}
            <Button variant="secondary" type="button" onClick={() => setRefunds((current) => [...current, { ...EMPTY_REFUND }])}>
              添加退款快照
            </Button>
          </fieldset>
          {error && canOperate ? <p className={styles.inlineAlert} role="alert">{error}</p> : null}
          <Button type="button" loading={pending} onClick={() => void submitRun()}>
            执行并记录对账
          </Button>
        </section>
      ) : null}

      <Drawer
        open={selectedRun !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedRun(null);
        }}
        side="right"
        title={selectedRun ? `对账差异 · ${selectedRun.channel}` : "对账差异"}
        description="只显示已经落库的差异事实，不推断未接入的渠道状态。"
      >
        {selectedRun ? (
          <div className={styles.detailStack}>
            <dl className={styles.details}>
              <div><dt>批次</dt><dd>{selectedRun.id}</dd></div>
              <div><dt>结果</dt><dd>{selectedRun.status === "matched" ? "已匹配" : "有差异"}</dd></div>
              <div><dt>条目</dt><dd>{selectedRun.item_count}</dd></div>
              <div><dt>差异</dt><dd>{selectedRun.difference_count}</dd></div>
            </dl>
            <ul className={styles.itemList}>
              {selectedRun.items.map((item) => (
                <li key={item.id}>
                  <strong>{item.kind === "payment" ? "支付" : "退款"} · {item.reference}</strong>
                  <span>{item.discrepancy}</span>
                  <small>本地 {item.local_status ?? "无"} · 渠道 {item.provider_status ?? "无"}</small>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
