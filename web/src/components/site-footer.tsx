import Link from "next/link";

import { Container } from "./container";
import styles from "./site-chrome.module.css";


export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.footerTop}>
          <div className={styles.footerCopy}>
            <strong>FateRadar · 命理档案</strong>
            <p>
              传统文化参考工具。结果由确定性命理计算与 AI 辅助表达共同完成，不替代医疗、法律、投资或其他专业意见。
            </p>
          </div>
          <nav className={styles.footerLinks} aria-label="页脚导航">
            <Link href="/methodology">方法与边界</Link>
            <Link href="/pricing">价格与交付</Link>
            <Link href="/privacy">隐私政策</Link>
            <Link href="/terms">服务条款</Link>
            <Link href="/support">帮助与售后</Link>
            <Link href="/account">账户与数据</Link>
          </nav>
        </div>
        <div className={styles.legal}>
          <span>© 2026 FateRadar · 开发期界面</span>
          <span>备案信息仅在正式审核完成后按真实资料展示</span>
        </div>
      </Container>
    </footer>
  );
}
