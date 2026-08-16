import { Suspense } from "react";

import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";

export default function QizhengRelationshipPage() {
  return (
    <Suspense fallback={<p>正在加载合盘…</p>}>
      <RelationshipTaskPage productId="qizheng" />
    </Suspense>
  );
}
