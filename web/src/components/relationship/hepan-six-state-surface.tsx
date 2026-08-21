"use client";

import Link from "next/link";

import { Status, type StatusState } from "@/components/ui/status";

export const HEPAN_SIX_STATES = [
  "loading",
  "empty",
  "error",
  "processing",
  "unavailable",
  "unauthorized",
] as const satisfies readonly StatusState[];

export type HepanSurfaceState = (typeof HEPAN_SIX_STATES)[number];

export const HEPAN_SIX_STATE_COPY: Record<
  HepanSurfaceState,
  { title: string; description: string }
> = {
  loading: {
    title: "正在读取合盘…",
    description: "页面只展示服务端公开摘要；状态与正文分开保存。",
  },
  empty: {
    title: "还没有可展示的盘面",
    description: "服务端尚未返回可展示的双方公开摘要，不会用演示数据填满合盘。",
  },
  error: {
    title: "读取失败，请重试",
    description: "读取合盘失败，请稍后重试。",
  },
  processing: {
    title: "正在处理合盘…",
    description: "双方事实已就绪，正在准备关系解读。不会提前展示未确认正文。",
  },
  unavailable: {
    title: "结果服务暂时不可用，不会展示未确认内容",
    description: "当前合盘结果服务暂不可用，不会展示未确认内容。",
  },
  unauthorized: {
    title: "需要登录才能看这份结果",
    description: "登录后才能查看这份合盘；不会重复提交双方出生资料。",
  },
};

export function isHepanSurfaceState(value: string | null | undefined): value is HepanSurfaceState {
  return Boolean(value && (HEPAN_SIX_STATES as readonly string[]).includes(value));
}

function HepanActions({
  state,
  onRetry,
}: {
  readonly state: HepanSurfaceState;
  readonly onRetry?: () => void;
}) {
  if (state === "unauthorized") {
    return <Link href="/auth/login">登录后继续</Link>;
  }
  if (state === "empty" || state === "error") {
    return (
      <>
        <button onClick={onRetry} type="button">
          重试
        </button>
        <Link data-variant="secondary" href="/bazi/hepan">
          返回合盘输入
        </Link>
      </>
    );
  }
  if (state === "unavailable") {
    return (
      <>
        <button onClick={onRetry} type="button">
          重试
        </button>
        <Link data-variant="secondary" href="/arts">
          查看术数总览
        </Link>
      </>
    );
  }
  return null;
}

export function HepanSixStateSurface({
  state,
  onRetry,
}: {
  readonly state: HepanSurfaceState;
  readonly onRetry?: () => void;
}) {
  const copy = HEPAN_SIX_STATE_COPY[state];
  return (
    <Status
      actions={<HepanActions onRetry={onRetry} state={state} />}
      description={copy.description}
      state={state}
      title={copy.title}
    />
  );
}
