import { FilePlus2, History } from "lucide-react";
import Link from "next/link";

import styles from "@/components/app-surface.module.css";
import { StatusPanel } from "@/components/status-panel";


export default function ProfilesPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>档案保存人，也保存每次确认。</h1>
        <div>
          <p>资料不会被“覆盖保存”。每次修改都会形成新的不可变档案版本，旧解读仍能回到当时使用的资料。</p>
          <div className={styles.metaLine}>
            <span><History aria-hidden="true" size={15} /> 不可变版本</span>
            <span><FilePlus2 aria-hidden="true" size={15} /> P0：一个本人档案</span>
          </div>
        </div>
      </header>

      <StatusPanel
        state="empty"
        title="还没有已保存的受测档案"
        description="你可以先以游客身份核对资料；登录且服务端接通后，才会创建正式档案版本并跨设备保存。"
        actionHref="/app/profile/new"
        actionLabel="开始建立档案"
      />

      <section className={styles.paper} aria-labelledby="version-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="version-title">档案状态怎么读</h2>
            <p>界面会把保存过程与最终版本分开，不让进度文案冒充成功。</p>
          </div>
        </div>
        <ul className={styles.legendList}>
          <li><span className={styles.stateTag}>草稿</span><p>还在浏览器会话内核对，不是正式 Profile Version。</p></li>
          <li><span className={styles.stateTag} data-state="processing">保存中</span><p>服务端正在确认资料与授权，页面保留输入并等待结果。</p></li>
          <li><span className={styles.stateTag} data-state="success">已保存版本</span><p>只有服务端成功创建不可变版本后才出现。</p></li>
          <li><span className={styles.stateTag} data-state="error">保存失败</span><p>说明失败原因与恢复路径，不把草稿写成已经保存。</p></li>
        </ul>
        <div className={styles.actionRow}>
          <Link className={styles.secondaryButton} href="/privacy">查看资料保存边界</Link>
        </div>
      </section>
    </div>
  );
}
