import { FileClock, ShieldCheck } from "lucide-react";
import Link from "next/link";

import styles from "@/components/app-surface.module.css";
import { StatusPanel } from "@/components/status-panel";


// 状态标签对应 lib/api 的 ReadingStatus；这里只解释服务端边界，不生成任何记录。
const states = [
  ["等待输入", "服务端要求补充本次解读所需事实，真实详情页会展示待填字段。", "idle"],
  ["准备解读", "事实已就绪，正在准备解读。", "processing"],
  ["事实已准备", "确定性事实已就绪，正在生成正文。", "processing"],
  ["正在接纳正文", "服务端正在接纳并固定正文；此时仍未交付。", "processing"],
  ["已交付", "只在服务端返回 accepted 且正文落库后出现。", "success"],
  ["已停止", "服务端已停止本次解读，需要重新发起。", "error"],
] as const;

export default function ReadingsPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>历史里保存的是版本，不是一串聊天消息。</h1>
        <div>
          <p>每个解读根可以包含初次解读、核对后的新版本与同盘追问。旧正文保持可回看，不会被新答案覆盖。</p>
          <div className={styles.metaLine}>
            <span><FileClock aria-hidden="true" size={15} /> 解读版本可回看</span>
            <span><ShieldCheck aria-hidden="true" size={15} /> 权益与交付分开</span>
          </div>
        </div>
      </header>

      <StatusPanel
        state="empty"
        title="目前没有可显示的真实解读"
        description="服务端暂无可列举的解读历史接口，真实结果通过 /app/readings/{reading_version_id} 打开。本页只用占位状态说明边界，不会伪造任何报告。"
        actionHref="/app/profile/new"
        actionLabel="先建立档案"
      />

      <section className={styles.paper} aria-labelledby="status-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="status-title">状态由服务端返回，本页不代为生成</h2>
            <p>下面是真实接口的状态含义，不是你的订单或解读历史。</p>
          </div>
        </div>
        <ul className={styles.legendList}>
          {states.map(([label, description, state]) => (
            <li key={label}>
              <span className={styles.stateTag} data-state={state}>{label}</span>
              <p>{description}</p>
            </li>
          ))}
        </ul>
        <p>服务端返回延迟或运行状态未知时，详情页会原样显示，本页不会替服务端补充状态。</p>
        <div className={styles.actionRow}>
          <Link className={styles.secondaryButton} href="/app">发起解读</Link>
        </div>
      </section>
    </div>
  );
}
