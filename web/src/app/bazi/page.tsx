import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "八字", description: "八字资料录入、四柱工作台与阅读入口。" };

export default function BaziPage() {
  return <ProductTaskPage productId="bazi" />;
}
