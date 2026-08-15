import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = {
  title: "太乙",
  description: "年度太乙年计盘结构事实入口。",
};

export default function TaiyiPage() {
  return <ProductTaskPage productId="taiyi" />;
}
