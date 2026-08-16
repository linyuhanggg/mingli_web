import Link from "next/link";

import type { CommerceSurfaceSpec } from "@/lib/secondary-surfaces";

import { SecondaryStatus } from "./secondary-status";
import { SecondarySurfaceFrame } from "./secondary-surface-frame";
import styles from "./secondary-surfaces.module.css";

export function CommerceSurface({ surface }: { readonly surface: CommerceSurfaceSpec }) {
  return (
    <SecondarySurfaceFrame eyebrow={surface.eyebrow} intro={surface.intro} title={surface.title}>
      <section aria-labelledby="commerce-boundaries" className={styles.boundaryPanel}>
        <h2 id="commerce-boundaries">当前边界</h2>
        <ul>
          {surface.facts.map((fact) => (
            <li key={fact}>{fact}</li>
          ))}
        </ul>
      </section>
      <SecondaryStatus
        action={surface.action}
        description={surface.statusDescription}
        state={surface.state}
        title={surface.statusTitle}
      />
      {surface.relatedLinks?.length ? (
        <nav aria-label="购买相关政策">
          <ul className={styles.linkList}>
            {surface.relatedLinks.map((link) => (
              <li key={link.href}>
                <Link href={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </SecondarySurfaceFrame>
  );
}
