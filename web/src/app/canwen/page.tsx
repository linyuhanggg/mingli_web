import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "多盘问答",
  description: "多盘问答已并入命盘合参；此路由保留重定向，历史任务与报告不受影响。",
};

// 2026-08-14 起多盘问答并入命盘合参（DESIGN §8.5）。
// next.config.ts 已在请求层把 /canwen 重定向到 /hecan；
// 页面级 redirect 作为深链兜底，保证路由与历史链接不失效。
export default function CanwenPage() {
  redirect("/hecan");
}
