import {
  AlertCircle,
  Ban,
  CheckCircle2,
  CircleHelp,
  Inbox,
  Loader2,
  LockKeyhole,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { useId, type ReactNode } from "react";

import styles from "./status.module.css";

export type CoreStatusState =
  | "loading"
  | "empty"
  | "ready"
  | "locked"
  | "need-input"
  | "error";

export type StatusState =
  | CoreStatusState
  | "processing"
  | "success"
  | "unavailable"
  | "unauthorized";

export const CORE_STATUS_STATES = [
  "loading",
  "empty",
  "ready",
  "locked",
  "need-input",
  "error",
] as const satisfies readonly CoreStatusState[];

/** All accepted states, including compatibility projections used by older flows. */
export const STATUS_STATES = [
  ...CORE_STATUS_STATES,
  "processing",
  "success",
  "unavailable",
  "unauthorized",
] as const satisfies readonly StatusState[];

export type StatusProps = {
  state: StatusState;
  title?: string;
  description?: string;
  actions?: ReactNode;
};

const copy: Record<StatusState, { title: string; description: string; icon: LucideIcon }> = {
  loading: {
    title: "正在同步出盘",
    description: "正在按真实盘面结构准备内容，请稍候。",
    icon: Loader2,
  },
  empty: {
    title: "还没有盘面",
    description: "完成录入后，这里会显示确定性盘面事实。",
    icon: Inbox,
  },
  ready: {
    title: "盘面已就绪",
    description: "盘面事实已经返回，可以继续核对时间层与说明。",
    icon: CheckCircle2,
  },
  locked: {
    title: "深读暂未解锁",
    description: "已返回的免费盘面事实仍可查看；锁定只作用于深读或付费时间层。",
    icon: LockKeyhole,
  },
  "need-input": {
    title: "需要补充信息",
    description: "当前输入处在边界口径，请确认后再继续计算。",
    icon: CircleHelp,
  },
  error: {
    title: "暂时无法完成",
    description: "这次请求没有成功。请检查输入或稍后重试，不会显示猜测结果。",
    icon: AlertCircle,
  },
  processing: {
    title: "正在处理",
    description: "任务正在运行，请稍候。",
    icon: Loader2,
  },
  success: {
    title: "已完成",
    description: "这一步已经顺利完成。",
    icon: CheckCircle2,
  },
  unavailable: {
    title: "暂不可用",
    description: "所需条件尚未满足，因此这个能力暂时不能使用。",
    icon: Ban,
  },
  unauthorized: {
    title: "需要登录",
    description: "登录后才能查看或继续这项操作。",
    icon: ShieldAlert,
  },
};

const busyStates: ReadonlySet<StatusState> = new Set(["loading", "processing"]);

export function Status({ state, title, description, actions }: StatusProps) {
  const headingId = useId();
  const descriptionId = useId();
  const definition = copy[state];
  const Icon = definition.icon;
  const resolvedTitle = title ?? definition.title;
  const resolvedDescription = description ?? definition.description;
  const isBusy = busyStates.has(state);

  return (
    <section
      className={`${styles.panel} ${styles[state]}`}
      data-core-state={CORE_STATUS_STATES.includes(state as CoreStatusState) ? state : undefined}
      data-state={state}
      role={state === "error" ? "alert" : "status"}
      aria-atomic="true"
      aria-busy={isBusy || undefined}
      aria-labelledby={headingId}
      aria-describedby={descriptionId}
    >
      <span aria-hidden="true" className={styles.icon}>
        <Icon aria-hidden="true" size={24} strokeWidth={1.75} />
      </span>
      <div>
        <h2 className={styles.title} id={headingId}>
          {resolvedTitle}
        </h2>
        <p className={styles.description} id={descriptionId}>
          {resolvedDescription}
        </p>
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </section>
  );
}
