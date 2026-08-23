import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "寻时定盘",
  description: "围绕未知时辰生成候选事实；此路由接到已开放的工具页。",
};

export default function TimeCheckPage() {
  redirect("/tools/time-check");
}
