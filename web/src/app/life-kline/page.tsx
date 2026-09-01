import type { Metadata } from "next";

import {
  LifeKlinePage,
  type LifeKlineViewState,
} from "@/components/life-kline-page";

export const metadata: Metadata = {
  title: "人生 K 线",
  description: "按档案查看可核对的时间层；权威事实不足时暂不绘制，并明确说明当前状态。",
};

const acceptedStates: ReadonlySet<string> = new Set([
  "need-input",
  "select-profile",
  "loading",
  "unsupported",
  "error",
] satisfies readonly LifeKlineViewState[]);

function asViewState(value: string | string[] | undefined): LifeKlineViewState {
  const candidate = Array.isArray(value) ? value[0] : value;
  return candidate && acceptedStates.has(candidate)
    ? (candidate as LifeKlineViewState)
    : "need-input";
}

export default async function LifeKlineRoute({
  searchParams,
}: {
  searchParams: Promise<{ state?: string | string[] }>;
}) {
  const { state } = await searchParams;
  const initialState = asViewState(state);
  return <LifeKlinePage initialState={initialState} key={initialState} />;
}
