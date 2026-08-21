import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "奇门", description: "填写问题和起局时间。" };

export default function QimenPage() {
  return <ProductTaskPage productId="qimen" />;
}
