import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "奇门", description: "奇门问题录入、九宫工作台与阅读入口。" };

export default function QimenPage() {
  return <ProductTaskPage productId="qimen" />;
}
