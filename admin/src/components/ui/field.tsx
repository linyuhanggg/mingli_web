import clsx from "clsx";
import {
  Children,
  cloneElement,
  isValidElement,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
  useId,
} from "react";

import styles from "./field.module.css";


type ControlProps = InputHTMLAttributes<HTMLInputElement> & {
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  className?: string;
};

export type FieldProps = {
  label: string;
  description?: string;
  error?: string;
  required?: boolean;
  disabledReason?: string;
  className?: string;
  children: ReactElement<ControlProps>;
};

export function Field({
  label,
  description,
  error,
  required,
  disabledReason,
  className,
  children,
}: FieldProps) {
  const generatedId = useId();
  const child = Children.only(children);
  if (!isValidElement<ControlProps>(child)) {
    throw new Error("Field requires a single control element");
  }

  const controlId = child.props.id ?? generatedId;
  const descriptionId = description ? `${controlId}-description` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const disabledId = disabledReason ? `${controlId}-disabled` : undefined;
  const describedBy = [child.props["aria-describedby"], descriptionId, errorId, disabledId]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={clsx(styles.field, className)}>
      <div className={styles.labelRow}>
        <label className={styles.label} htmlFor={controlId}>
          {label}
        </label>
        {required ? (
          <span className={styles.required} aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
      </div>
      {description ? (
        <p className={styles.description} id={descriptionId}>
          {description}
        </p>
      ) : null}
      {cloneElement(child, {
        id: controlId,
        className: clsx(styles.control, child.props.className),
        // Keep the child's own aria-invalid when there is no error; never wipe
        // an existing invalid state just because this Field has no message.
        "aria-invalid": error ? true : child.props["aria-invalid"],
        "aria-describedby": describedBy || undefined,
        // `required` is reflected as both the native constraint and ARIA.
        "aria-required": required ? true : child.props["aria-required"],
        required: required ? true : child.props.required,
      })}
      {error ? (
        <p className={styles.error} id={errorId} role="alert">
          {error}
        </p>
      ) : null}
      {disabledReason ? (
        <p className={styles.disabledReason} id={disabledId}>
          {disabledReason}
        </p>
      ) : null}
    </div>
  );
}

export type { ReactNode };
