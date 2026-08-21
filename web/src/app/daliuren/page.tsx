import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "大六壬", description: "填写问题和起课时间。" };

export default function DaliurenPage() {
  return <ProductTaskPage productId="daliuren" />;
}
