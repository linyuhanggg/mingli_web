import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "六爻", description: "六爻问题录入、起卦工作台与阅读入口。" };

export default function LiuyaoPage() {
  return <ProductTaskPage productId="liuyao" />;
}
