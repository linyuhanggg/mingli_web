import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "命盘合参", description: "八字、紫微、七政的择术、互证与整合入口；原多盘问答已并入。" };

export default function HecanPage() {
  return <ProductTaskPage productId="hecan" />;
}
