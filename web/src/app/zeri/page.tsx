import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "择日",
  description: "日期范围、候选淘汰与可解释排序事实入口；此路由接到已开放的择日页。",
};

export default function ZeriPage() {
  redirect("/selection");
}
