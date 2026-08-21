import Link from "next/link";

import { Container } from "./container";
import styles from "./site-chrome.module.css";


const productLinks = [
  { href: "/arts", label: "术数总览" },
  { href: "/hecan", label: "命盘合参" },
  { href: "/tools", label: "工具" },
  { href: "/daily", label: "每日" },
] as const;

const contentLinks = [
  { href: "/library", label: "知识内容" },
  { href: "/methodology", label: "方法与边界" },
  { href: "/support", label: "帮助与支持" },
] as const;

const accountLinks = [
  { href: "/account", label: "账户" },
  { href: "/privacy", label: "隐私政策" },
  { href: "/terms", label: "服务条款" },
] as const;

function FooterLinkGroup({
  ariaLabel,
  links,
  title,
}: {
  ariaLabel: string;
  links: readonly { href: string; label: string }[];
  title: string;
}) {
  return (
    <nav aria-label={ariaLabel} className={styles.footerColumn}>
      <h2>{title}</h2>
      {links.map((item) => (
        <Link href={item.href} key={item.href}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function SiteFooter({ home = false }: { home?: boolean }) {
  return (
    <footer className={styles.footer} data-home-chrome={home ? "true" : undefined}>
      <Container>
        <div className={styles.footerTop}>
          <div className={styles.footerCopy}>
            <div className={styles.footerBrand}>
              <span className={styles.symbol} aria-hidden="true">
                <span>命</span>
              </span>
              <strong>命理工具</strong>
            </div>
            <p>
              {home
                ? "先形成可复现的盘面事实，再沿古籍证据展开有依据、有边界、可核对的说明。"
                : "中性测试版公共入口：先形成可复现的盘面事实，再提供有依据、有边界、可核对的说明。"}
            </p>
          </div>
          <div className={styles.footerColumns}>
            <FooterLinkGroup ariaLabel="产品入口" links={productLinks} title="产品入口" />
            <FooterLinkGroup ariaLabel="知识与帮助" links={contentLinks} title="知识与帮助" />
            <FooterLinkGroup ariaLabel="账户与政策" links={accountLinks} title="账户与政策" />
          </div>
        </div>
        <div className={styles.legal}>
          <span>© 2026 命理工具测试版</span>
          <span>内容仅作传统文化参考，不替代医疗、法律、投资或其他专业意见。</span>
        </div>
      </Container>
    </footer>
  );
}
