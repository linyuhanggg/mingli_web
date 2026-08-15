import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "七政", description: "七政资料录入、星盘工作台与阅读入口。" };

export default function QizhengPage() {
  return <ProductTaskPage productId="qizheng" />;
}
