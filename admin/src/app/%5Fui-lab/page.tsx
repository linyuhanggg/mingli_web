import { notFound } from "next/navigation";

import { AdminShell } from "@/components/admin-shell";
import { AdminUiLabWorkbench } from "@/components/admin-ui-lab-workbench";

export default function AdminUiLabPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <AdminShell
      title="UI Lab"
      duty="开发与测试环境的 Admin 页面族验收中心。所有 Fixture 都有永久标识。"
      demoRole="support"
    >
      <AdminUiLabWorkbench />
    </AdminShell>
  );
}
