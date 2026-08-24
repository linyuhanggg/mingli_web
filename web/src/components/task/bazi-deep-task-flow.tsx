"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";

import {
  ApiError,
  bindReadingFulfillment,
  createBaziDeepCheckout,
  recordConsent,
  createIdempotencyKey,
  getBaziDeepCheckout,
  pollReading,
  startBaziDeepReading,
  type DeliveryState,
  type ReadingStatus,
} from "@/lib/api";
import { useOptionalAccountSession } from "@/components/account-session-context";
import { CURRENT_POLICY_VERSION } from "@/lib/policy";
import { ReadingResult } from "@/components/readings/reading-result";
import { Status } from "@/components/ui/status";

import styles from "./bazi-deep-task-flow.module.css";

const POLL_MS = 2_000;

function isStalePolicyVersion(reason: unknown): boolean {
  return (
    reason instanceof ApiError
    && reason.status === 400
    && reason.message === "Policy version is not current"
  );
}

async function recordPurchaseConsents(): Promise<void> {
  for (const policy_key of ["privacy", "terms"] as const) {
    await recordConsent({
      policy_key,
      policy_version: CURRENT_POLICY_VERSION,
      context: "purchase",
    });
  }
}


/**
 * These are product-facing states. They intentionally do not reuse internal
 * ReadingJob strings. Queue/worker states come from the bounded
 * `delivery_state` projection; `awaiting_fulfillment` is shown while the
 * server-owned checkout/binding operation is in flight.
 */
export type BaziDeepTaskState =
  | "preview_loading"
  | "free"
  | "unauthenticated"
  | "unpaid"
  | "awaiting_fulfillment"
  | "checkout_pending"
  | "checkout_unavailable"
  | "checkout_failed"
  | "queued"
  | "running"
  | "succeeded"
  | "failed";

export type BaziDeepTaskFlowProps = {
  previewReadingId: string;
  profileVersionId: string;
  query: string;
  startedAt?: number;
  onBack: () => void;
  onRestart?: () => void;
};

type PollMode = "preview" | "deep";

export function stateForReadingStatus(
  status: ReadingStatus,
  mode: PollMode,
): BaziDeepTaskState {
  if (status === "accepted") {
    return mode === "preview" ? "free" : "succeeded";
  }
  if (status === "prepared" || status === "completing") {
    return mode === "preview" ? "preview_loading" : "running";
  }
  if (status === "input_ready") {
    return mode === "preview" ? "preview_loading" : "awaiting_fulfillment";
  }
  return "failed";
}

/**
 * Prefer the server's bounded delivery projection over ReadingVersion.status.
 * The latter describes the version, not the paid Job's queue/worker state.
 */
export function stateForDeliveryState(
  deliveryState: DeliveryState | undefined,
  currentState: BaziDeepTaskState,
): BaziDeepTaskState {
  switch (deliveryState) {
    case "payment_required":
      return "awaiting_fulfillment";
    case "queued":
      return "queued";
    case "processing":
      return "running";
    case "delivered":
      return "succeeded";
    case "waiting_input":
    case "delayed":
    case "failed":
      return "failed";
    case "not_required":
    case undefined:
      if (currentState === "queued" || currentState === "running") return currentState;
      return "failed";
  }
}

function statusDescription(state: BaziDeepTaskState): { title: string; text: string } {
  switch (state) {
    case "preview_loading":
      return { title: "正在准备免费盘面", text: "盘面正在生成，离开页面后仍会继续处理。" };
    case "free":
      return { title: "免费盘面已就绪", text: "下面展示服务端返回的盘面与依据；浏览器不重新排盘。" };
    case "unauthenticated":
      return { title: "深读需要登录", text: "登录只用于接管当前任务和后续履约，不会重复提交出生资料。" };
    case "unpaid":
      return { title: "尚未确认付费", text: "可从当前免费盘面发起服务端结账；未确认到账前不会绑定履约，也不会读取深读结果。" };
    case "awaiting_fulfillment":
      return { title: "正在准备履约", text: "服务端正在创建当前盘面的深读任务和结账会话。" };
    case "checkout_pending":
      return { title: "等待支付确认", text: "请完成服务端提供的支付步骤；只有后端确认 Payment 后才会绑定深读。" };
    case "checkout_unavailable":
      return { title: "支付暂时不可用", text: "当前支付适配器没有返回可用结账，不会创建成功付款，也不会启动深读履约。" };
    case "checkout_failed":
      return { title: "支付会话未完成", text: "结账会话没有完成确认；可以稍后重试，当前没有读取深读结果。" };
    case "queued":
      return { title: "已进入深读队列", text: "付款权益已绑定到当前任务，服务端会继续处理。" };
    case "running":
      return { title: "深读生成中", text: "事实整理和正文生成正在服务端进行，请稍候。" };
    case "succeeded":
      return { title: "深读已交付", text: "最终结果已经固定保存，可以随时回看。" };
    case "failed":
      return { title: "任务暂未完成", text: "没有展示未确认的深读内容；可按页面提示重试或稍后恢复。" };
  }
}

function errorHttpStatus(error: unknown): number | null {
  return error instanceof ApiError ? error.status : null;
}

function readableError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "登录状态已失效，请重新登录后再继续。";
    if (error.status === 403) return "服务端没有确认可用的付费权益，当前未绑定任何履约。";
    if (error.status === 404) return "任务不存在或已不属于当前会话，未加载任何结果。";
    if (error.status === 409) return "当前任务的履约状态已变化，请刷新后恢复。";
    if (error.status === 422) return "支付请求参数尚未完成服务端校验，请稍后重试。";
    if (error.status === 503) return "支付入口暂时不可用，当前没有创建成功付款。";
  }
  if (error instanceof Error && error.message) return error.message;
  return "服务暂时无法完成这一步，请稍后重试。";
}

function isTerminalStatus(status: ReadingStatus): boolean {
  return status === "delayed" || status === "runtime_unknown" || status === "terminal_stopped";
}

function safeCheckoutRedirect(value: string | null | undefined): string | null {
  if (!value) return null;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try {
    return new URL(value).protocol === "https:" ? value : null;
  } catch {
    return null;
  }
}

export function BaziDeepTaskFlow({
  previewReadingId,
  profileVersionId,
  query,
  startedAt,
  onBack,
  onRestart,
}: BaziDeepTaskFlowProps) {
  const router = useRouter();
  const session = useOptionalAccountSession();
  const [state, setState] = useState<BaziDeepTaskState>("preview_loading");
  const [deepReadingId, setDeepReadingId] = useState<string | null>(null);
  const [checkoutOrderId, setCheckoutOrderId] = useState<string | null>(null);
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const deepStartKeyRef = useRef<string | null>(null);
  const checkoutStartKeyRef = useRef<string | null>(null);
  const fulfillmentKeyRef = useRef<string | null>(null);
  const bindingPaymentKeyRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      if (cancelled) return;
      try {
        const summary = await pollReading(previewReadingId);
        if (cancelled) return;
        setError(null);
    setErrorStatus(null);
        const nextState = stateForReadingStatus(summary.status, "preview");
        setState(nextState);
        if (summary.status === "accepted" || isTerminalStatus(summary.status)) return;
        timer = setTimeout(run, POLL_MS);
      } catch (reason) {
        if (cancelled) return;
        setState("failed");
        setErrorStatus(errorHttpStatus(reason));
        setError(readableError(reason));
      }
    }

    void run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [previewReadingId, retryKey]);

  const accountState = session?.state.status;
  const accessState = (
    state === "free"
    || state === "unauthenticated"
    || state === "unpaid"
  )
    ? accountState === "checking"
      ? state
      : accountState === "signedIn" ? "unpaid" : "unauthenticated"
    : state;

  const bindConfirmedPayment = useCallback(async (readingId: string, paymentId: string) => {
    const normalizedPaymentId = paymentId.trim();
    if (!normalizedPaymentId) return false;
    const bindingKey = `${readingId}:${normalizedPaymentId}`;
    if (bindingPaymentKeyRef.current === bindingKey) return true;
    bindingPaymentKeyRef.current = bindingKey;
    setError(null);
    setErrorStatus(null);
    setState("awaiting_fulfillment");
    try {
      const fulfillmentKey = fulfillmentKeyRef.current ?? createIdempotencyKey();
      fulfillmentKeyRef.current = fulfillmentKey;
      await bindReadingFulfillment(
        readingId,
        { payment_id: normalizedPaymentId },
        fulfillmentKey,
      );
      if (!mountedRef.current) return false;
      setState("queued");
      return true;
    } catch (reason) {
      if (!mountedRef.current) return false;
      setState("failed");
      setErrorStatus(errorHttpStatus(reason));
        setError(readableError(reason));
      return false;
    }
  }, []);

  async function beginCheckout() {
    if (accessState !== "unpaid" || session?.state.status !== "signedIn") return;
    if (!profileVersionId) {
      setState("checkout_failed");
      setError("当前资料版本尚未确认，不能创建深读结账。");
      return;
    }
    setError(null);
    setErrorStatus(null);
    setCheckoutUrl(null);
    setState("awaiting_fulfillment");
    try {
      const startKey = deepStartKeyRef.current ?? createIdempotencyKey();
      deepStartKeyRef.current = startKey;
      const deep = await startBaziDeepReading(
        {
          profile_version_id: profileVersionId,
          ...(query.trim() ? { query: query.trim() } : {}),
        },
        startKey,
      );
      if (!mountedRef.current) return;
      setDeepReadingId(deep.reading_version_id);

      await recordPurchaseConsents();
      if (!mountedRef.current) return;

      const checkoutKey = checkoutStartKeyRef.current ?? createIdempotencyKey();
      checkoutStartKeyRef.current = checkoutKey;
      const checkout = await createBaziDeepCheckout(
        { reading_version_id: deep.reading_version_id },
        checkoutKey,
      );
      if (!mountedRef.current) return;
      if (
        checkout.order.product_id !== "bazi-deep"
        || checkout.order.reading_version_id !== deep.reading_version_id
      ) {
        throw new Error("服务端结账目标与当前深读不一致，未绑定任何付款。");
      }
      setCheckoutOrderId(checkout.order.order_id);
      const redirectUrl = safeCheckoutRedirect(checkout.redirect_url);
      if (checkout.redirect_url && !redirectUrl) {
        throw new Error("服务端支付地址无效，未打开任何支付页面。");
      }
      setCheckoutUrl(redirectUrl);
      if (checkout.payment_id?.trim()) {
        await bindConfirmedPayment(deep.reading_version_id, checkout.payment_id);
      } else if (checkout.gateway_status === "unavailable") {
        setState("checkout_unavailable");
      } else if (checkout.gateway_status === "failed") {
        setState("checkout_failed");
      } else {
        setState("checkout_pending");
      }
    } catch (reason) {
      if (!mountedRef.current) return;
      if (isStalePolicyVersion(reason)) {
        router.replace("/auth/consent");
        return;
      }
      setState("checkout_failed");
      setErrorStatus(errorHttpStatus(reason));
      setError(readableError(reason));
    }
  }

  useEffect(() => {
    if (!checkoutOrderId || !deepReadingId || state !== "checkout_pending") return;
    const orderId = checkoutOrderId;
    const readingId = deepReadingId;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      if (cancelled) return;
      try {
        const checkout = await getBaziDeepCheckout(orderId);
        if (cancelled) return;
        if (
          checkout.order.product_id !== "bazi-deep"
          || checkout.order.reading_version_id !== readingId
        ) {
          setState("checkout_failed");
          setError("服务端结账目标与当前深读不一致，未绑定任何付款。");
          return;
        }
        const redirectUrl = safeCheckoutRedirect(checkout.redirect_url);
        if (checkout.redirect_url && !redirectUrl) {
          setState("checkout_failed");
          setError("服务端支付地址无效，未打开任何支付页面。");
          return;
        }
        setCheckoutUrl(redirectUrl);
        if (checkout.payment_id?.trim()) {
          await bindConfirmedPayment(readingId, checkout.payment_id);
          return;
        }
        if (checkout.gateway_status === "unavailable") {
          setState("checkout_unavailable");
          return;
        }
        if (checkout.gateway_status === "failed") {
          setState("checkout_failed");
          return;
        }
        timer = setTimeout(run, POLL_MS);
      } catch (reason) {
        if (cancelled) return;
        setState("checkout_failed");
        setErrorStatus(errorHttpStatus(reason));
        setError(readableError(reason));
      }
    }

    void run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [bindConfirmedPayment, checkoutOrderId, deepReadingId, state]);

  useEffect(() => {
    if (!deepReadingId || !["queued", "running"].includes(state)) return;
    const readingId = deepReadingId;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      if (cancelled) return;
      try {
        const summary = await pollReading(readingId);
        if (cancelled) return;
        setError(null);
    setErrorStatus(null);
        const nextState = summary.delivery_state
          ? stateForDeliveryState(summary.delivery_state, state)
          : summary.status === "input_ready"
            ? state
            : stateForReadingStatus(summary.status, "deep");
        setState(nextState);
        if (
          nextState === "succeeded"
          || nextState === "failed"
          || summary.status === "accepted"
          || isTerminalStatus(summary.status)
        ) return;
        timer = setTimeout(run, POLL_MS);
      } catch (reason) {
        if (cancelled) return;
        setState("failed");
        setErrorStatus(errorHttpStatus(reason));
        setError(readableError(reason));
      }
    }

    void run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [deepReadingId, state]);

  const phase = statusDescription(accessState);
  const sessionChecking = session?.state.status === "checking";
  const showDeepResult = accessState === "succeeded"
    && deepReadingId !== null
    && session?.state.status === "signedIn";

  function retry() {
    setError(null);
    setErrorStatus(null);
    if (checkoutOrderId) {
      bindingPaymentKeyRef.current = null;
      setState("checkout_pending");
      return;
    }
    if (deepReadingId) {
      setDeepReadingId(null);
      setState("unpaid");
      return;
    }
    setRetryKey((value) => value + 1);
  }

  return (
    <section className={styles.flow} aria-labelledby="bazi-deep-task-title">
      <header className={styles.toolbar}>
        <button className={styles.backButton} onClick={onBack} type="button">
          <ArrowLeft aria-hidden="true" size={17} />
          返回录入
        </button>
        <h2 className={styles.title} id="bazi-deep-task-title">八字工作台</h2>
        <p className={styles.toolbarNote}>当前任务状态由服务端确认</p>
      </header>

      {accessState !== "preview_loading" ? (
      <section className={styles.section} aria-labelledby="bazi-deep-status-title">
        <div className={styles.statusCopy}>
          <h2 id="bazi-deep-status-title">任务进度</h2>
          <p>{phase.text}</p>
        </div>
        {accessState === "failed" ? (
          <Status
            actions={
              errorStatus === 401 || errorStatus === 403 ? (
                <Link href="/auth/login">登录后继续</Link>
              ) : (
                <>
                  <button onClick={retry} type="button">重试状态读取</button>
                  <button data-variant="secondary" onClick={onBack} type="button">返回修改资料</button>
                </>
              )
            }
            description={error ?? phase.text}
            state={
              errorStatus === 401 || errorStatus === 403
                ? "unauthorized"
                : errorStatus === 404
                  ? "empty"
                  : errorStatus === 503
                    ? "unavailable"
                    : "error"
            }
            title={
              errorStatus === 401 || errorStatus === 403
                ? "需要登录才能看这份结果"
                : errorStatus === 404
                  ? "还没有可展示的盘面"
                  : errorStatus === 503
                    ? "结果服务暂时不可用，不会展示未确认内容"
                    : phase.title
            }
          />
        ) : null}
        {accessState === "awaiting_fulfillment" ? (
          <Status state="processing" title={phase.title} description={phase.text} />
        ) : null}
        {accessState === "checkout_pending" ? (
          <Status state="processing" title={phase.title} description={phase.text} />
        ) : null}
        {accessState === "checkout_unavailable" ? (
          <Status
            actions={<Link href="/pricing">查看交付说明</Link>}
            description={error ?? phase.text}
            state="unavailable"
            title={phase.title}
          />
        ) : null}
        {accessState === "checkout_failed" ? (
          <Status state="error" title={phase.title} description={error ?? phase.text} />
        ) : null}
        {accessState === "queued" || accessState === "running" ? (
          <Status state="processing" title={phase.title} description={phase.text} />
        ) : null}
        {accessState === "succeeded" ? (
          <Status state="success" title={phase.title} description={phase.text} />
        ) : null}
      </section>
      ) : null}

      {(
        accessState === "preview_loading"
        || accessState === "free"
        || accessState === "unauthenticated"
        || accessState === "unpaid"
        || accessState === "awaiting_fulfillment"
        || accessState === "checkout_pending"
        || accessState === "checkout_unavailable"
        || accessState === "checkout_failed"
        || accessState === "queued"
        || accessState === "running"
        || showDeepResult
      ) ? (
        <section className={styles.section} aria-labelledby="bazi-free-result-title">
          <div className={styles.statusCopy}>
            <h2 id="bazi-free-result-title">免费盘面</h2>
            <p>盘面和事实由服务端排定；这里不展示尚未生成的深读内容。</p>
          </div>
          <div className={styles.result}>
            <ReadingResult
              readingId={previewReadingId}
              onRestart={onRestart}
              startedAt={startedAt}
            />
          </div>
        </section>
      ) : null}

      {accessState === "free" && sessionChecking ? (
        <Status state="loading" title="正在确认深读资格" description="只确认账户状态，不会创建深读任务。" />
      ) : null}

      {accessState === "unauthenticated" ? (
        <section className={styles.section} aria-labelledby="bazi-deep-login-title">
          <Status
            actions={<Link href="/auth/login">登录后继续</Link>}
            description={statusDescription("unauthenticated").text}
            state="unauthorized"
            title="深读需要登录"
          />
        </section>
      ) : null}

      {accessState === "unpaid" ? (
        <section className={styles.section} aria-labelledby="bazi-deep-offer-title">
          <div className={styles.statusCopy}>
            <h2 id="bazi-deep-offer-title">八字深读</h2>
            <p>深读会绑定当前免费盘面的资料版本，完成后再交付结构化报告与追问权益。</p>
          </div>
          <Status state="unavailable" title={statusDescription("unpaid").title} description={statusDescription("unpaid").text} />
          <p className={styles.securityNote}>不会创建 mock 订单、不会接受手工付款号，也不会在未付款时请求或展示深读结果。支付适配器不可用时会明确停在这里。</p>
          <div className={styles.actionRow}>
            <button className={styles.primaryAction} onClick={() => void beginCheckout()} type="button">
              开始安全结账
            </button>
            <Link className={styles.secondaryAction} href="/pricing">查看交付说明</Link>
          </div>
        </section>
      ) : null}

      {accessState === "checkout_pending" ? (
        <section className={styles.section} aria-labelledby="bazi-checkout-pending-title">
          <div className={styles.statusCopy}>
            <h2 id="bazi-checkout-pending-title">等待支付确认</h2>
            <p>完成支付后，本页面会读取当前账户的结账状态；只有服务端返回 confirmed payment_id 才会绑定履约。</p>
          </div>
          {checkoutUrl ? (
            <div className={styles.actionRow}>
              <a className={styles.primaryAction} href={checkoutUrl} rel="noreferrer">打开支付页面</a>
            </div>
          ) : null}
          <p className={styles.securityNote}>页面不展示订单号或付款标识；未确认前不会请求或展示深读结果。</p>
        </section>
      ) : null}

      {accessState === "checkout_unavailable" ? (
        <section className={styles.section} aria-labelledby="bazi-checkout-unavailable-title">
          <Status
            actions={(
              <>
                <button onClick={retry} type="button">重新检查支付</button>
                <Link data-variant="secondary" href="/pricing">查看交付说明</Link>
              </>
            )}
            description={error ?? statusDescription("checkout_unavailable").text}
            state="unavailable"
            title="支付暂时不可用"
          />
          <p className={styles.securityNote}>当前 Fake/不可用适配器不会被当成成功付款；请稍后重试或查看交付说明。</p>
        </section>
      ) : null}

      {accessState === "checkout_failed" ? (
        <section className={styles.section} aria-labelledby="bazi-checkout-failed-title">
          <Status state="error" title="支付会话未完成" description={error ?? statusDescription("checkout_failed").text} />
          <p className={styles.securityNote}>没有确认 Payment，不会绑定履约，也不会请求深读结果。</p>
          <div className={styles.actionRow}>
            <button className={styles.primaryAction} onClick={retry} type="button">重试结账状态</button>
            <button className={styles.secondaryAction} onClick={onBack} type="button">返回修改资料</button>
          </div>
        </section>
      ) : null}

      {showDeepResult ? (
        <section className={styles.section} aria-labelledby="bazi-deep-result-title">
          <div className={styles.statusCopy}>
            <h2 id="bazi-deep-result-title">八字深读结果</h2>
            <p>下面的最终报告由服务端接受后提供；前台不自行生成或补写结论。</p>
          </div>
          <div className={styles.result}>
            <ReadingResult readingId={deepReadingId} />
          </div>
        </section>
      ) : null}
    </section>
  );
}
