"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Container } from "./container";
import { SiteFooter } from "./site-footer";
import { MobileNavigation, PublicShellChrome, SiteHeader } from "./site-header";
import { CORE_STATUS_STATES, type CoreStatusState } from "./ui/status";
import styles from "./public-page-shell.module.css";

type BreadcrumbItem = Readonly<{
  href?: string;
  label: string;
}>;

const EXACT_BREADCRUMBS: Readonly<Record<string, readonly BreadcrumbItem[]>> = {
  "/about": [{ label: "关于" }],
  "/account": [{ label: "我的" }],
  "/arts": [{ label: "术数总览" }],
  "/auth/consent": [{ label: "确认政策" }],
  "/auth/login": [{ label: "登录" }],
  "/auth/recover": [{ label: "找回密码" }],
  "/auth/register": [{ label: "注册" }],
  "/auth/set-password": [{ label: "设置密码" }],
  "/auth/verify": [{ label: "验证账号" }],
  "/bazi": [{ label: "八字" }],
  "/bazi/hepan": [{ href: "/bazi", label: "八字" }, { label: "八字合盘" }],
  "/checkout": [{ label: "确认订单" }],
  "/daily": [{ label: "每日已下线" }],
  "/daliuren": [{ label: "大六壬" }],
  "/fengshui": [{ label: "风水" }],
  "/fortune": [{ label: "运势" }],
  "/hecan": [{ label: "命盘合参" }],
  "/jianxiang": [{ label: "见相" }],
  "/library": [{ label: "知识内容已下线" }],
  "/life-kline": [{ label: "人生 K 线" }],
  "/liuyao": [{ label: "六爻" }],
  "/login": [{ label: "登录" }],
  "/luming-nayin": [{ label: "禄命纳音" }],
  "/meihua": [{ label: "梅花易数" }],
  "/methodology": [{ label: "方法与边界" }],
  "/pricing": [{ label: "价格与交付" }],
  "/privacy": [{ label: "隐私政策" }],
  "/qimen": [{ label: "奇门遁甲" }],
  "/qizheng": [{ label: "七政四余" }],
  "/qizheng/hepan": [{ href: "/qizheng", label: "七政四余" }, { label: "七政合盘" }],
  "/register": [{ label: "注册" }],
  "/selection": [{ label: "择日" }],
  "/support": [{ label: "帮助与支持" }],
  "/taiyi": [{ label: "太乙" }],
  "/terms": [{ label: "服务条款" }],
  "/tools": [{ label: "工具" }],
  "/wenshi": [{ label: "问事合参" }],
  "/ziwei": [{ label: "紫微斗数" }],
  "/ziwei/hepan": [{ href: "/ziwei", label: "紫微斗数" }, { label: "紫微合盘" }],
};

const DYNAMIC_BREADCRUMBS: readonly Readonly<{
  breadcrumbs: readonly BreadcrumbItem[];
  matches: RegExp;
}>[] = [
  {
    matches: /^\/checkout\/[^/]+$/,
    breadcrumbs: [{ href: "/checkout", label: "确认订单" }, { label: "订单详情" }],
  },
  { matches: /^\/invite\/[^/]+$/, breadcrumbs: [{ label: "邀请有礼" }] },
  {
    matches: /^\/library\/[^/]+$/,
    breadcrumbs: [{ label: "知识内容已下线" }],
  },
  { matches: /^\/share\/[^/]+$/, breadcrumbs: [{ label: "分享结果" }] },
  {
    matches: /^\/tools\/[^/]+$/,
    breadcrumbs: [{ href: "/tools", label: "工具" }, { label: "工具详情" }],
  },
  { matches: /^\/workbench\/[^/]+$/, breadcrumbs: [{ label: "结果工作台" }] },
];

const BREADCRUMB_STATUS_LABELS: Readonly<Record<CoreStatusState, string>> = {
  loading: "LOADING",
  empty: "EMPTY",
  ready: "READY",
  locked: "LOCKED",
  "need-input": "NEED-INPUT",
  error: "ERROR",
};

function getBreadcrumbs(pathname: string) {
  const normalizedPathname = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return (
    EXACT_BREADCRUMBS[normalizedPathname]
    ?? DYNAMIC_BREADCRUMBS.find(({ matches }) => matches.test(normalizedPathname))?.breadcrumbs
    ?? null
  );
}

function isCoreStatusState(value: string): value is CoreStatusState {
  return CORE_STATUS_STATES.includes(value as CoreStatusState);
}

function getBreadcrumbStatus(requestedStatus?: string): CoreStatusState | null {
  return requestedStatus !== undefined && isCoreStatusState(requestedStatus)
    ? requestedStatus
    : null;
}

function Breadcrumb({
  pathname,
  requestedStatus,
}: Readonly<{ pathname: string; requestedStatus?: string }>) {
  const breadcrumbs = getBreadcrumbs(pathname);
  if (!breadcrumbs) return null;
  const status = getBreadcrumbStatus(requestedStatus);

  return (
    <div className={styles.breadcrumbBar}>
      <Container>
        <nav aria-label="面包屑" className={styles.breadcrumb}>
          <ol className={styles.breadcrumbList}>
            <li>
              <Link href="/">首页</Link>
            </li>
            {breadcrumbs.map(({ href, label }, index) => {
              const current = index === breadcrumbs.length - 1;
              return (
                <li className={styles.breadcrumbItem} key={`${href ?? "current"}-${label}`}>
                  <span aria-hidden="true" className={styles.breadcrumbSeparator}>/</span>
                  {current || !href ? (
                    <span aria-current="page">{label}</span>
                  ) : (
                    <Link href={href}>{label}</Link>
                  )}
                </li>
              );
            })}
            {status ? (
              <li className={styles.breadcrumbStatusItem}>
                <span
                  aria-label={`当前状态：${BREADCRUMB_STATUS_LABELS[status]}`}
                  className={styles.breadcrumbStatus}
                  data-state={status}
                >
                  {BREADCRUMB_STATUS_LABELS[status]}
                </span>
              </li>
            ) : null}
          </ol>
        </nav>
      </Container>
    </div>
  );
}

export function PublicPageShell({
  breadcrumbStatus,
  children,
}: Readonly<{ breadcrumbStatus?: string; children: ReactNode }>) {
  const pathname = usePathname() || "/";
  const isHome = pathname === "/";
  const breadcrumb =
    breadcrumbStatus === undefined ? (
      <Breadcrumb pathname={pathname} />
    ) : (
      <Breadcrumb pathname={pathname} requestedStatus={breadcrumbStatus} />
    );

  return (
    <PublicShellChrome>
      <div className={styles.shell}>
        <SiteHeader />
        {breadcrumb}
        {children}
        <MobileNavigation pathname={pathname} />
        <SiteFooter home={isHome} />
      </div>
    </PublicShellChrome>
  );
}
