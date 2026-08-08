import Link from "next/link";

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
          登录 / 账户
        </Link>
      </Container>
    </header>
  );
}
