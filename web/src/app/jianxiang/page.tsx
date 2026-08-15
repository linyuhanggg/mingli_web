import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "见相", description: "见相授权采集、结构化观察与阅读入口。" };

export default function JianxiangPage() {
  return <ProductTaskPage productId="jianxiang" />;
}
