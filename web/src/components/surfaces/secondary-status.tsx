import { CircleOff, Inbox, LogIn } from "lucide-react";
import Link from "next/link";
import { useId } from "react";

import type { SecondarySurfaceLink, SecondarySurfaceState } from "@/lib/secondary-surfaces";

import styles from "./secondary-surfaces.module.css";

const stateIcons = {
  unavailable: CircleOff,
  "need-login": LogIn,
  empty: Inbox,
} as const;

type SecondaryStatusProps = {
  readonly state: SecondarySurfaceState;
  readonly title: string;
  readonly description: string;
  readonly action?: SecondarySurfaceLink;
};

export function SecondaryStatus({ state, title, description, action }: SecondaryStatusProps) {
  const headingId = useId();
  const descriptionId = useId();
  const Icon = stateIcons[state];

  return (
    <section
      aria-describedby={descriptionId}
      aria-labelledby={headingId}
      className={styles.status}
      data-state={state}
      role="status"
    >
      <span aria-hidden="true" className={styles.statusIcon}>
        <Icon aria-hidden="true" size={24} strokeWidth={1.75} />
      </span>
      <div>
        <h2 id={headingId}>{title}</h2>
        <p id={descriptionId}>{description}</p>
        {action ? (
          <Link className={styles.primaryLink} href={action.href}>
            {action.label}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
