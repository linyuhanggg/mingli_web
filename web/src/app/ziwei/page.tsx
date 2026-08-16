import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "紫微", description: "紫微资料录入、十二宫工作台与阅读入口。" };

export default function ZiweiPage() {
  return <ProductTaskPage productId="ziwei" />;
}
