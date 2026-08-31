import clsx from "clsx";

import styles from "./local-loader.module.css";

export type LocalLoaderVariant = "dots" | "dot-matrix";

export type LocalLoaderProps = Readonly<{
  className?: string;
  /** Required for standalone loaders. Omit only when nearby text already names the busy state. */
  label?: string;
  variant?: LocalLoaderVariant;
}>;

export function LocalLoader({
  className,
  label,
  variant = "dots",
}: LocalLoaderProps) {
  const dots = variant === "dot-matrix" ? 4 : 3;

  return (
    <span
      aria-hidden={label ? undefined : "true"}
      aria-label={label}
      className={clsx(styles.loader, styles[variant], className)}
      data-loader-variant={variant}
      role={label ? "status" : undefined}
    >
      {Array.from({ length: dots }, (_, index) => (
        <span aria-hidden="true" className={styles.dot} key={index} />
      ))}
    </span>
  );
}
