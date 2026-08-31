"use client";

import clsx from "clsx";
import { Check, CircleAlert } from "lucide-react";
import { Slot } from "radix-ui";
import {
  Children,
  cloneElement,
  isValidElement,
  type ButtonHTMLAttributes,
  type MouseEvent,
  type ReactNode,
} from "react";

import styles from "./button.module.css";
import { LocalLoader } from "./local-loader";


export type ButtonVariant =
  | "primary"
  | "secondary"
  | "quiet"
  | "signal"
  | "danger"
  | "icon"
  /** Compatibility alias. New call sites use `quiet`. */
  | "ghost"
  /** Compatibility alias. New call sites use `danger`. */
  | "destructive";

export type ButtonSize = "sm" | "md" | "lg";
export type ButtonState = "idle" | "loading" | "success" | "error";

type ButtonBaseProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  /** Compatibility shortcut. Prefer `state="loading"` for width-stable task buttons. */
  loading?: boolean;
  state?: ButtonState;
  loadingLabel?: ReactNode;
  successLabel?: ReactNode;
  errorLabel?: ReactNode;
  asChild?: boolean;
  size?: ButtonSize;
  children: ReactNode;
};

type IconButtonProps = Omit<ButtonBaseProps, "aria-label"> & {
  variant: "icon";
  "aria-label": string;
};

type TextButtonProps = ButtonBaseProps & {
  variant?: Exclude<ButtonVariant, "icon">;
};

export type ButtonProps = IconButtonProps | TextButtonProps;

export function Button({
  variant = "primary",
  loading = false,
  state,
  loadingLabel = "正在处理",
  successLabel = "已完成",
  errorLabel = "操作失败",
  asChild = false,
  size = "md",
  disabled,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const accessibleLabel = props["aria-label"];
  if (
    variant === "icon" &&
    (typeof accessibleLabel !== "string" || accessibleLabel.trim().length === 0)
  ) {
    throw new Error('Button variant="icon" requires a non-empty aria-label.');
  }

  const resolvedState = state ?? (loading ? "loading" : "idle");
  const isLoading = resolvedState === "loading";
  const isStateful = state !== undefined;
  const isDisabled = Boolean(disabled || isLoading);

  function renderContent(content: ReactNode) {
    if (!isStateful) {
      return (
        <>
          {isLoading ? <LocalLoader /> : null}
          {content}
        </>
      );
    }

    return (
      <span className={styles.stateContent}>
        <span aria-hidden="true" className={styles.stateIcon}>
          {resolvedState === "loading" ? <LocalLoader /> : null}
          {resolvedState === "success" ? <Check size={18} strokeWidth={2.4} /> : null}
          {resolvedState === "error" ? <CircleAlert size={18} strokeWidth={2.2} /> : null}
        </span>
        <span aria-live="polite" className={styles.stateLabels}>
          {([
            ["idle", content],
            ["loading", loadingLabel],
            ["success", successLabel],
            ["error", errorLabel],
          ] as const).map(([labelState, label]) => (
            <span
              aria-hidden={resolvedState === labelState ? undefined : "true"}
              className={styles.stateLabel}
              data-visible={resolvedState === labelState ? "true" : undefined}
              key={labelState}
            >
              {label}
            </span>
          ))}
        </span>
      </span>
    );
  }

  if (asChild) {
    // Radix Slot clones exactly one element. When loading we inject the
    // feedback into that element's children so it renders alongside the
    // consumer's content rather than as a sibling that would break the Slot.
    const childNodes = Children.toArray(children);
    if (childNodes.length !== 1 || !isValidElement(childNodes[0])) {
      throw new Error("Button asChild requires exactly one React element child.");
    }
    const child = childNodes[0];
    const slottable = isValidElement<{ children?: ReactNode }>(child)
      ? cloneElement(child, undefined, renderContent(child.props.children))
      : child;

    // An `asChild` target (a link, a form control, …) cannot carry the native
    // `disabled` attribute, so block it three ways: remove it from the tab
    // order, stop pointer events via CSS, and swallow click activation.
    const inert = isDisabled
      ? {
          "aria-disabled": true,
          tabIndex: -1,
          onClickCapture: (event: MouseEvent<HTMLElement>) => {
            event.preventDefault();
            event.stopPropagation();
          },
        }
      : {};

    return (
      <Slot.Root
        className={clsx(styles.button, styles[variant], styles[size], className)}
        data-loading={isLoading ? "true" : undefined}
        data-state={resolvedState}
        data-size={size}
        data-variant={variant}
        aria-busy={isLoading || undefined}
        {...props}
        {...inert}
      >
        {slottable}
      </Slot.Root>
    );
  }

  return (
    <button
      className={clsx(styles.button, styles[variant], styles[size], className)}
      data-loading={isLoading ? "true" : undefined}
      data-state={resolvedState}
      data-size={size}
      data-variant={variant}
      aria-busy={isLoading || undefined}
      disabled={isDisabled}
      type={type}
      {...props}
    >
      {renderContent(children)}
    </button>
  );
}
