import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = {
  title: "择日",
  description: "日期范围、候选淘汰与可解释排序事实入口。",
};

export default function SelectionPage() {
  return <ProductTaskPage productId="selection" />;
}
