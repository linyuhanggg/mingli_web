import clsx from "clsx";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ComponentPropsWithoutRef } from "react";

import styles from "./ui.module.css";


type ButtonLinkProps = ComponentPropsWithoutRef<typeof Link> & {
  variant?: "primary" | "secondary" | "text";
};

export function ButtonLink({
  className = "",
  variant = "primary",
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={clsx(styles.button, styles[variant], className)}
      {...props}
    >
      <span>{props.children}</span>
      <ArrowUpRight aria-hidden="true" size={17} strokeWidth={1.8} />
    </Link>
  );
}
