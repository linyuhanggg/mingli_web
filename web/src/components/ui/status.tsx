import {
  AlertCircle,
  Ban,
  CheckCircle2,
  Inbox,
  Loader2,
  LockKeyhole,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { useId } from "react";

import styles from "./status.module.css";


export type StatusState =
  | "loading"
  | "empty"
  | "error"
  | "processing"
  | "success"
  | "unavailable"
  | "unauthorized"
  | "locked";

export const STATUS_STATES = [
  "loading",
  "empty",
  "error",
  "processing",
  "success",
  "unavailable",
  "unauthorized",
  "locked",
] as const satisfies readonly StatusState[];

export type StatusProps = {
  state: StatusState;
  title?: string;
  description?: string;
};

const copy: Record<StatusState, { title: string; description: string; icon: LucideIcon }> = {
  loading: {
    title: "正在载入…",
    description: "内容正在准备，请稍候…",
    icon: Loader2,
  },
  empty: {
    title: "暂无内容",
    description: "完成第一步后，这里会显示新的记录。",
    icon: Inbox,
  },
  error: {
    title: "出现错误",
    description: "这次请求没有成功，请重试或检查输入。",
    icon: AlertCircle,
  },
  processing: {
    title: "正在处理…",
    description: "任务正在运行，请稍候…",
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
  locked: {
    title: "已锁定",
    description: "当前内容被锁定，暂不能修改或访问。",
    icon: LockKeyhole,
  },
};

const busyStates: ReadonlySet<StatusState> = new Set(["loading", "processing"]);

export function Status({ state, title, description }: StatusProps) {
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
    </section>
  );
}
