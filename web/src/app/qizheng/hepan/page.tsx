import type { Metadata } from "next";
import { Suspense } from "react";

import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";
import { Status } from "@/components/ui/status";

export const metadata: Metadata = { title: "七政双人合盘", description: "填写双方资料和关系。" };

export default function QizhengRelationshipPage() {
  return (
    <Suspense
      fallback={(
        <Status
          description="正在准备七政合盘输入与结果状态，请稍候。"
          state="loading"
          title="正在加载七政合盘"
        />
      )}
    >
      <RelationshipTaskPage productId="qizheng" />
    </Suspense>
  );
}
