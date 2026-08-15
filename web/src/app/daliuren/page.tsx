import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "大六壬", description: "大六壬问题录入、课盘工作台与阅读入口。" };

export default function DaliurenPage() {
  return <ProductTaskPage productId="daliuren" />;
}
