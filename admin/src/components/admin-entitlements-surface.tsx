"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { useAdminStaff } from "@/components/admin-shell";
import {
  Button,
  Dialog,
  DialogFooter,
  Field,
  Status,
  Table,
  type TableColumn,
  type TableRow,
} from "@/components/ui";
import { adminFetch, type StaffRole } from "@/lib/api";
import type {
  AdminEntitlementAction,
  AdminEntitlementAdjustmentResponse,
  AdminEntitlementEventsResponse,
} from "@/lib/admin-entitlements";

import styles from "./admin-entitlements-surface.module.css";

const COLUMNS: TableColumn[] = [
  { key: "id", header: "事件", sortable: true },
  { key: "owner", header: "用户", sortable: true },
  { key: "entitlement", header: "权益", sortable: true },
  { key: "kind", header: "事件类型", sortable: true },
  { key: "quantity", header: "数量", sortable: true },
  { key: "source", header: "来源" },
  { key: "createdAt", header: "发生时间", sortable: true },
];

type SurfaceState = "loading" | "ready" | "empty" | "error" | "forbidden" | "unavailable";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function kindCopy(value: string): string {
  return {
    GRANT: "发放",
    RESERVE: "占用",
    CONSUME: "消费",
    RELEASE: "释放",
    REVERSE: "冲正",
    EXPIRE: "过期",
  }[value] ?? value;
}

function actionCopy(value: AdminEntitlementAction): string {
  return {
    grant: "发放",
    compensate: "补偿",
    revoke: "撤回",
  }[value];
}

export function AdminEntitlementsSurface({ role }: { role?: StaffRole }) {
  const sessionStaff = useAdminStaff();
  const effectiveRole = role ?? sessionStaff?.role;
  const canAdjust = effectiveRole === "finance" || effectiveRole === "ops" || effectiveRole === "superadmin";
  const [state, setState] = useState<SurfaceState>("loading");
  const [data, setData] = useState<AdminEntitlementEventsResponse>({ events: [] });
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [ownerUserId, setOwnerUserId] = useState("");
  const [entitlementId, setEntitlementId] = useState("");
  const [action, setAction] = useState<AdminEntitlementAction>("grant");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("");
  const [sourceRef, setSourceRef] = useState("");
  const [targetRef, setTargetRef] = useState("");

  const load = useCallback(async () => {
    const response = await adminFetch<AdminEntitlementEventsResponse>(
      "/api/v1/admin/entitlements/events/recent",
    );
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
    setState(response.data.events.length > 0 ? "ready" : "empty");
    setError(null);
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await adminFetch<AdminEntitlementEventsResponse>(
        "/api/v1/admin/entitlements/events/recent",
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
      setState(response.data.events.length > 0 ? "ready" : "empty");
      setError(null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit() {
    if (!canAdjust) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    const response = await adminFetch<AdminEntitlementAdjustmentResponse>(
      "/api/v1/admin/entitlements/events",
      {
        method: "POST",
        body: JSON.stringify({
          owner_user_id: ownerUserId.trim(),
          entitlement_id: entitlementId.trim(),
          action,
          quantity: Number(quantity),
          reason: reason.trim(),
          source_ref: sourceRef.trim(),
          target_ref: targetRef.trim() || null,
        }),
      },
    );
    if (!response.ok) {
      setError(response.title);
      setSubmitting(false);
      return;
    }
    setResult(response.data.created ? "权益账本事件已追加" : "权益账本事件已幂等重放");
    setSubmitting(false);
  }

  const rows = useMemo<TableRow[]>(
    () =>
      data.events.map((item) => ({
        id: item.id,
        owner: item.owner_user_id,
        entitlement: item.entitlement_id,
        kind: kindCopy(item.kind),
        quantity: item.quantity,
        source: `${item.source_type} · ${item.source_ref}`,
        createdAt: formatDate(item.created_at),
      })),
    [data.events],
  );

  const notice =
    state === "loading" ? (
      <Status state="loading" title="正在读取权益账本…" description="只显示服务端追加式事件，不推断余额或补造用户记录。" />
    ) : state === "forbidden" ? (
      <Status state="locked" title="无权限" description="权益账本只允许财务、运营和超级管理员查看或调整。" />
    ) : state === "unavailable" ? (
      <Status state="unavailable" title="权益平台暂不可用" description="页面不显示假余额或假发放结果。" />
    ) : state === "error" ? (
      <Status state="error" title="权益账本读取失败" description={error ?? "请求失败，请重试。"} />
    ) : state === "empty" ? (
      <Status state="empty" title="暂无权益账本事件" description="正式 GRANT/RESERVE/CONSUME 等事件产生后，这里会显示不可变轨迹。" />
    ) : (
      <Status state="success" title="权益账本已接入" description="列表只展示服务端事件；调整命令必须填写对象、原因和唯一来源编号。" />
    );

  return (
    <div className={styles.stack} data-state={state} data-staff-role={effectiveRole ?? "session"}>
      {notice}
      {state === "ready" || state === "empty" ? (
        <section className={styles.panel} aria-labelledby="entitlements-title">
          <div className={styles.heading}>
            <div>
              <h2 id="entitlements-title">最近权益事件</h2>
              <p>只显示正式账本事实；页面不计算余额、不展示原始支付通知，也不把演示数据混入生产页面。</p>
            </div>
            <span className={styles.badge}>追加式账本</span>
          </div>
          <Table
            caption="最近权益账本事件"
            columns={COLUMNS}
            rows={rows}
            filterLabel="筛选权益事件"
            filterPlaceholder="例如：用户、权益、事件类型或来源…"
            pageSize={20}
            emptyState="当前没有权益账本事件"
          />
          {canAdjust ? (
            <form
              className={styles.form}
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                setConfirmOpen(true);
              }}
            >
              <label className={styles.field}>
                <span>用户 ID</span>
                <input aria-label="用户 ID" value={ownerUserId} onChange={(event) => setOwnerUserId(event.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>权益 ID</span>
                <input aria-label="权益 ID" value={entitlementId} onChange={(event) => setEntitlementId(event.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>调整动作</span>
                <select aria-label="调整动作" value={action} onChange={(event) => setAction(event.target.value as AdminEntitlementAction)}>
                  <option value="grant">发放</option>
                  <option value="compensate">补偿</option>
                  <option value="revoke">撤回</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>数量</span>
                <input aria-label="数量" type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>来源编号</span>
                <input aria-label="来源编号" value={sourceRef} onChange={(event) => setSourceRef(event.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>目标编号（可选）</span>
                <input aria-label="目标编号（可选）" value={targetRef} onChange={(event) => setTargetRef(event.target.value)} />
              </label>
              <div className={styles.actions}>
                <Dialog
                  open={confirmOpen}
                  onOpenChange={(open) => {
                    setConfirmOpen(open);
                    if (open) {
                      setReason("");
                      setResult(null);
                      setError(null);
                      return;
                    }
                    if (result) void load();
                    setReason("");
                    setResult(null);
                    setError(null);
                  }}
                  title={`追加权益事件 · ${ownerUserId || "未选择用户"}`}
                  description="账本事件只追加、不改写历史；确认后将记录对象、来源、原因与操作员工。"
                  trigger={
                    <Button
                      type="submit"
                      disabled={
                        !ownerUserId.trim() ||
                        !entitlementId.trim() ||
                        !sourceRef.trim() ||
                        Number(quantity) < 1
                      }
                    >
                      复核并追加
                    </Button>
                  }
                >
                  <dl className={styles.impactSummary}>
                    <div><dt>影响对象</dt><dd>{ownerUserId}</dd></div>
                    <div><dt>权益与动作</dt><dd>{entitlementId} · {actionCopy(action)} · {quantity}</dd></div>
                    <div><dt>来源编号</dt><dd>{sourceRef}</dd></div>
                    <div><dt>审计结果</dt><dd>追加不可变账本事件并记录操作原因</dd></div>
                  </dl>
                  <Field
                    label="操作原因"
                    description="至少 4 个字；请说明业务依据，不要填写秘密信息。"
                    required
                  >
                    <input
                      type="text"
                      name="entitlement-adjustment-reason"
                      autoComplete="off"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      minLength={4}
                    />
                  </Field>
                  {error ? <Status state="error" title="权益命令失败" description={error} /> : null}
                  {result ? <Status state="success" title="审计已完成" description={result} /> : null}
                  <DialogFooter>
                    <Button variant="ghost" type="button" onClick={() => setConfirmOpen(false)}>取消</Button>
                    <Button
                      type="button"
                      loading={submitting}
                      disabled={reason.trim().length < 4 || Boolean(result)}
                      aria-describedby="entitlement-confirm-help"
                      onClick={() => void submit()}
                    >
                      确认并记录审计
                    </Button>
                  </DialogFooter>
                  <p className={styles.submitHelp} id="entitlement-confirm-help">
                    {result ? "操作已完成，可关闭确认层。" : "填写至少 4 个字的原因后可确认。"}
                  </p>
                </Dialog>
              </div>
            </form>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
