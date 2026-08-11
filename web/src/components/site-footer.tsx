import Link from "next/link";

import { Container } from "./container";
import styles from "./site-chrome.module.css";


const coreLinks = [
  { href: "/app/profile/new", label: "在线八字排盘" },
  { href: "/app/bazi", label: "双人合盘分析" },
  { href: "/app/profiles", label: "命理双子数据库" },
  { href: "/methodology", label: "学术中心与古籍库" },
] as const;

const stanceLinks = [
  { href: "/methodology", label: "倪海厦天纪体系" },
  { href: "/methodology", label: "《紫微斗数全书》考据" },
  { href: "/privacy", label: "无恐吓与破灾营销" },
  { href: "/privacy", label: "数据端到端加密" },
] as const;

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.footerTop}>
          <div className={styles.footerCopy}>
            <div className={styles.footerBrand}>
              <span className={styles.symbol} aria-hidden="true">
                <span>命</span>
              </span>
              <strong>FateRadar</strong>
            </div>
            <p>
              东方编辑档案：把时间变成私密、可核对的个人档案。结合确定性命理核心与现代 AI 表达，不替代医疗、法律、投资或其他专业意见。
            </p>
          </div>
          <div className={styles.footerColumns}>
            <nav className={styles.footerColumn} aria-label="核心应用">
              <h2>核心应用</h2>
              {coreLinks.map((item) => (
                <Link href={item.href} key={`${item.href}-${item.label}`}>
                  {item.label}
                </Link>
              ))}
            </nav>
            <nav className={styles.footerColumn} aria-label="学术与立场">
              <h2>学术与立场</h2>
              {stanceLinks.map((item) => (
                <Link href={item.href} key={`${item.href}-${item.label}`}>
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className={styles.footerColumn}>
              <h2>平台承诺</h2>
              <p>
                本平台旨在通过现代化信息技术传承中华传统易学文化，所有解读仅供学术文化研究与理智思考参考。
              </p>
            </div>
          </div>
        </div>
        <div className={styles.legal}>
          <span>© 2026 FateRadar（命盘 AI）. 保留所有权利</span>
          <nav className={styles.legalLinks} aria-label="法律链接">
            <Link href="/terms">免责声明</Link>
            <Link href="/privacy">隐私政策</Link>
            <Link href="/support">学术安全</Link>
          </nav>
        </div>
      </Container>
    </footer>
  );
}
