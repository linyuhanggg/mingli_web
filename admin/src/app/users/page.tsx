import { AdminShell } from "@/components/admin-shell";
import ui from "@/components/ui.module.css";

export default function Page() {
  return (
    <AdminShell title="用户档案" duty="只读查询用户与档案。敏感字段默认打码。">
      <section className={ui.paper}>
        <p className={ui.empty}>用户列表尚未接入。Phase B 接 Admin users API。</p>
      </section>
    </AdminShell>
  );
}
