"use client";

import { useState, type ReactNode } from "react";

import { Status, type StatusState } from "@/components/ui/status";

import styles from "./bazi-result-six-states.module.css";

const SIX_STATES = [
  "loading",
  "empty",
  "error",
  "processing",
  "unavailable",
  "unauthorized",
] as const satisfies readonly StatusState[];

const COPY: Record<(typeof SIX_STATES)[number], { title: string; description: string; action: string }> = {
  loading: {
    title: "正在读取结果…",
    description: "页面只展示服务端公开摘要；状态与正文分开保存。",
    action: "",
  },
  empty: {
    title: "还没有可展示的盘面",
    description: "服务端尚未返回可展示的公开摘要，不会用演示数据填满结果。",
    action: "重试",
  },
  error: {
    title: "读取失败，请重试",
    description: "读取结果失败，请稍后重试。",
    action: "重试",
  },
  processing: {
    title: "正在处理…",
    description: "事实已就绪，正在准备解读。不会提前展示未确认正文。",
    action: "",
  },
  unavailable: {
    title: "结果服务暂时不可用，不会展示未确认内容",
    description: "当前结果服务暂不可用，不会展示未确认内容。",
    action: "重试",
  },
  unauthorized: {
    title: "需要登录才能看这份结果",
    description: "登录后才能查看这份结果；不会重复提交出生资料。",
    action: "登录后继续",
  },
};

type BaziLabState = "ready" | (typeof SIX_STATES)[number];

export function BaziResultSixStates({ children }: { readonly children: ReactNode }) {
  const [state, setState] = useState<BaziLabState>("ready");
  const details = state === "ready" ? null : COPY[state];

  return (
    <div className={styles.wrap}>
      <nav aria-label="结果页六态" className={styles.nav}>
        <button
          aria-pressed={state === "ready"}
          className={styles.tab}
          onClick={() => setState("ready")}
          type="button"
        >
          已返回事实
        </button>
        {SIX_STATES.map((item) => (
          <button
            aria-pressed={state === item}
            className={styles.tab}
            key={item}
            onClick={() => setState(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </nav>
      {state === "ready" || !details ? (
        children
      ) : (
        <Status
          actions={
            details.action ? (
              <button type="button">{details.action}</button>
            ) : null
          }
          description={details.description}
          state={state}
          title={details.title}
        />
      )}
    </div>
  );
}
