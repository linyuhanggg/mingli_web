import type { Metadata } from "next";
import { Suspense } from "react";

import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";

export const metadata: Metadata = { title: "八字双人合盘", description: "填写双方资料和关系。" };

export default function BaziRelationshipPage() {
  return (
    <Suspense fallback={<p>正在加载合盘…</p>}>
      <RelationshipTaskPage productId="bazi" />
    </Suspense>
  );
}
