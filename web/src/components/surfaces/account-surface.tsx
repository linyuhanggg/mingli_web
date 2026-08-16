import Link from "next/link";

import { AppPageHeader } from "@/components/app-page-header";
import type { AccountSurfaceSpec } from "@/lib/secondary-surfaces";

import { SecondaryStatus } from "./secondary-status";
import styles from "./secondary-surfaces.module.css";

export function AccountSurface({ surface }: { readonly surface: AccountSurfaceSpec }) {
  return (
    <div className={styles.accountPage}>
      <AppPageHeader description={surface.intro} title={surface.title} />
      <section aria-label={surface.eyebrow} className={styles.accountPanel}>
        <SecondaryStatus
          action={surface.action}
          description={surface.statusDescription}
          state={surface.state}
          title={surface.statusTitle}
        />

        {surface.relatedLinks?.length ? (
          <nav aria-label="设置分类">
            <ul className={styles.linkList}>
              {surface.relatedLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href}>{link.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </section>
    </div>
  );
}
