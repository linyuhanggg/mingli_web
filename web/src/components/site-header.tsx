import Link from "next/link";
import { LogIn } from "lucide-react";

import { BrandMark } from "./brand-mark";
import { Container } from "./container";
import styles from "./site-chrome.module.css";


const navigation = [
  { href: "/pricing", label: "价格" },
  { href: "/methodology", label: "方法" },
  { href: "/support", label: "支持" },
] as const;

export function SiteHeader() {
  return (
    <>
      <a className={styles.skipLink} href="#main-content">
        跳到主要内容
      </a>
      <header className={styles.header}>
        <Container className={styles.headerInner}>
          <BrandMark />
          <nav className={styles.nav} aria-label="主导航">
            {navigation.map((item) => (
              <Link href={item.href} key={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <Link className={styles.accountLink} href="/account">
            <LogIn aria-hidden="true" size={17} />
            <span>登录 / 账户</span>
          </Link>
        </Container>
      </header>
    </>
  );
}
