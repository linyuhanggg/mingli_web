import { AdminShell } from "@/components/admin-shell";
import ui from "@/components/ui.module.css";

export default function Page() {
  return (
    <AdminShell title="解读任务" duty="看失败与卡住任务。重试受领域门禁。">
      <section className={ui.paper}>
        <p className={ui.empty}>解读任务列表尚未接入。Phase B 接 readings API。</p>
      </section>
    </AdminShell>
  );
}
