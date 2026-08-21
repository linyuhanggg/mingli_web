"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import { Button, Drawer, Field, Status, Table, type TableColumn, type TableRow } from "@/components/ui";
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
const SNAPSHOT_STATUS_LABELS = {
  pending: "待处理",
  succeeded: "已成功",
  failed: "已失败",
  refunded: "已退款",
} as const;

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
  const [channelError, setChannelError] = useState<string | undefined>();
  const [reasonError, setReasonError] = useState<string | undefined>();
  const channelRef = useRef<HTMLInputElement>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);

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
    if (!channel.trim()) {
      const message = "请填写对账渠道。";
      setChannelError(message);
      setError(message);
      channelRef.current?.focus();
      return;
    }
    if (normalizedReason.length < 4) {
      const message = "请填写至少 4 个字的对账原因。";
      setReasonError(message);
      setError(message);
      reasonRef.current?.focus();
      return;
    }
    setChannelError(undefined);
    setReasonError(undefined);
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

  const stateNotice = result ? (
    <Status compact state="success" title={result} description="本次命令已通过服务端权限、CSRF 和审计边界。" />
  ) : state === "loading" ? (
      <Status compact state="loading" title="正在读取对账批次…" description="只显示服务端已经保存的对账事实。" />
    ) : state === "forbidden" ? (
      <Status compact state="locked" title="无权限" description="对账只允许财务、运营或超级管理员访问。" />
    ) : state === "unavailable" ? (
      <Status compact state="unavailable" title="对账平台暂不可用" description="页面保留只读结构，不显示假差异或假金额。" />
    ) : state === "error" ? (
      <Status compact state="error" title="对账读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status compact state="empty" title="暂无对账批次" description="完成一次已验签快照对账后，这里会显示批次和差异。" />
    ) : null;

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {stateNotice}
      {state === "ready" ? <section className={styles.panel} aria-labelledby="reconciliation-list-title">
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
          filter={{
            label: "按对账结果筛选",
            rowKey: "status",
            options: [
              { value: "", label: "全部" },
              { value: "已匹配", label: "已匹配" },
              { value: "有差异", label: "有差异" },
            ],
          }}
          pageSize={10}
          emptyState="没有符合筛选条件的对账批次"
          onRowActivate={rows.length > 0 ? openRun : undefined}
          rowActionLabel="查看差异"
        />
      </section> : null}

      {canOperate && state === "ready" ? (
        <section className={styles.panel} aria-labelledby="reconciliation-command-title">
          <div className={styles.heading}>
            <div>
              <h2 id="reconciliation-command-title">执行对账</h2>
              <p>仅提交已由渠道适配器验签、归一化的快照；本页不执行第三方渠道验签。</p>
            </div>
            <span className={styles.badge}>需审计</span>
          </div>
          <div className={styles.formGrid}>
            <Field
              className={styles.workbenchField}
              label="渠道"
              description="填写已验签快照所属的渠道适配器。"
              error={channelError}
              required
            >
              <input
                ref={channelRef}
                name="reconciliationChannel"
                autoComplete="off"
                value={channel}
                onChange={(event) => {
                  setChannel(event.target.value);
                  if (event.target.value.trim()) setChannelError(undefined);
                }}
              />
            </Field>
            <Field
              className={`${styles.workbenchField} ${styles.wideField}`}
              label="操作原因"
              description="至少 4 个字；原因会随本次对账写入审计。"
              error={reasonError}
              required
            >
              <textarea
                ref={reasonRef}
                name="reconciliationReason"
                autoComplete="off"
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value);
                  if (event.target.value.trim().length >= 4) setReasonError(undefined);
                }}
                minLength={4}
                placeholder="说明本次对账的来源和业务原因…"
              />
            </Field>
          </div>

          <fieldset className={styles.snapshotGroup}>
            <legend>支付快照</legend>
            {payments.map((item, index) => (
              <div className={styles.snapshotRow} key={`payment-${index}`}>
                <Field className={styles.workbenchField} label="交易号">
                  <input name={`payments.${index}.transaction_id`} autoComplete="off" value={item.transaction_id} onChange={(event) => updatePayment(index, "transaction_id", event.target.value)} />
                </Field>
                <Field className={styles.workbenchField} label="状态">
                  <select name={`payments.${index}.status`} autoComplete="off" value={item.status} onChange={(event) => updatePayment(index, "status", event.target.value)}>
                    {Object.entries(SNAPSHOT_STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </Field>
                <Field className={styles.workbenchField} label="金额（分）">
                  <input name={`payments.${index}.amount_minor`} autoComplete="off" type="number" min={0} value={item.amount_minor} onChange={(event) => updatePayment(index, "amount_minor", event.target.value)} />
                </Field>
                <Field className={styles.workbenchField} label="币种">
                  <input name={`payments.${index}.currency`} autoComplete="off" maxLength={3} value={item.currency} onChange={(event) => updatePayment(index, "currency", event.target.value)} />
                </Field>
                <Button aria-label={`移除支付快照 ${index + 1}`} variant="ghost" type="button" onClick={() => setPayments((current) => current.filter((_, itemIndex) => itemIndex !== index))} disabled={payments.length === 1}>
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
                <Field className={styles.workbenchField} label="退款号">
                  <input name={`refunds.${index}.refund_id`} autoComplete="off" value={item.refund_id} onChange={(event) => updateRefund(index, "refund_id", event.target.value)} />
                </Field>
                <Field className={styles.workbenchField} label="支付交易号">
                  <input name={`refunds.${index}.payment_transaction_id`} autoComplete="off" value={item.payment_transaction_id} onChange={(event) => updateRefund(index, "payment_transaction_id", event.target.value)} />
                </Field>
                <Field className={styles.workbenchField} label="状态">
                  <select name={`refunds.${index}.status`} autoComplete="off" value={item.status} onChange={(event) => updateRefund(index, "status", event.target.value)}>
                    {Object.entries(SNAPSHOT_STATUS_LABELS)
                      .filter(([value]) => value !== "refunded")
                      .map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                  </select>
                </Field>
                <Field className={styles.workbenchField} label="金额（分）">
                  <input name={`refunds.${index}.amount_minor`} autoComplete="off" type="number" min={0} value={item.amount_minor} onChange={(event) => updateRefund(index, "amount_minor", event.target.value)} />
                </Field>
                <Field className={styles.workbenchField} label="币种">
                  <input name={`refunds.${index}.currency`} autoComplete="off" maxLength={3} value={item.currency} onChange={(event) => updateRefund(index, "currency", event.target.value)} />
                </Field>
                <Button aria-label={`移除退款快照 ${index + 1}`} variant="ghost" type="button" onClick={() => setRefunds((current) => current.filter((_, itemIndex) => itemIndex !== index))}>
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
