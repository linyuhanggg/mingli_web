"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Container } from "./container";
import { SiteFooter } from "./site-footer";
import { MobileNavigation, PublicShellChrome, SiteHeader } from "./site-header";
import styles from "./public-page-shell.module.css";

const ROUTE_LABELS: Readonly<Record<string, string>> = {
  account: "我的",
  bazi: "八字",
  daily: "每日",
  daliuren: "大六壬",
  hecan: "命盘合参",
  jianxiang: "见相",
  knowledge: "知识内容",
  library: "知识内容",
  liuyao: "六爻",
  login: "登录",
  meihua: "梅花易数",
  methodology: "方法与边界",
  qimen: "奇门遁甲",
  qizheng: "七政四余",
  result: "结果工作台",
  tools: "工具",
  wenshi: "问事合参",
  ziwei: "紫微斗数",
};

function Breadcrumb({ pathname }: Readonly<{ pathname: string }>) {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return null;

  return (
    <div className={styles.breadcrumbBar}>
      <Container>
        <nav aria-label="面包屑" className={styles.breadcrumb}>
          <Link href="/">首页</Link>
          {segments.map((segment, index) => {
            const href = `/${segments.slice(0, index + 1).join("/")}`;
            const current = index === segments.length - 1;
            const label = ROUTE_LABELS[segment] ?? decodeURIComponent(segment);

            return (
              <span className={styles.breadcrumbItem} key={href}>
                <span aria-hidden="true" className={styles.breadcrumbSeparator}>/</span>
                {current ? (
                  <span aria-current="page">{label}</span>
                ) : (
                  <Link href={href}>{label}</Link>
                )}
              </span>
            );
          })}
        </nav>
      </Container>
    </div>
  );
}

export function PublicPageShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname() || "/";
  const isHome = pathname === "/";

  return (
    <PublicShellChrome>
      <div className={styles.shell}>
        <SiteHeader />
        <Breadcrumb pathname={pathname} />
        {children}
        <MobileNavigation pathname={pathname} />
        <SiteFooter home={isHome} />
      </div>
    </PublicShellChrome>
  );
}
