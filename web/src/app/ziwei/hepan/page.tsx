import type { Metadata } from "next";
import { Suspense } from "react";

import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";

export const metadata: Metadata = { title: "紫微双人合盘", description: "填写双方资料和关系。" };

export default function ZiweiRelationshipPage() {
  return (
    <Suspense fallback={<p>正在加载合盘…</p>}>
      <RelationshipTaskPage productId="ziwei" />
    </Suspense>
  );
}
