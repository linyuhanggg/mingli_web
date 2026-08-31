"use client";

import clsx from "clsx";
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


export type ButtonVariant =
  | "primary"
  | "secondary"
  | "quiet"
  | "signal"
  | "danger"
  | "icon"
  /** Admin compatibility alias: retains the dense toolbar treatment. */
  | "ghost"
  /** Admin compatibility alias: retains the explicit destructive treatment. */
  | "destructive";

export type ButtonSize = "sm" | "md" | "lg";

type ButtonBaseProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  loading?: boolean;
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

  const isDisabled = Boolean(disabled || loading);
  const spinner = loading ? <span aria-hidden="true" className={styles.spinner} /> : null;

  if (asChild) {
    // Radix Slot clones exactly one element. When loading we inject the
    // spinner into that element's children so it renders alongside the
    // consumer's content rather than as a sibling that would break the Slot.
    const childNodes = Children.toArray(children);
    if (childNodes.length !== 1 || !isValidElement(childNodes[0])) {
      throw new Error("Button asChild requires exactly one React element child.");
    }
    const child = childNodes[0];
    const slottable =
      loading && isValidElement<{ children?: ReactNode }>(child)
        ? cloneElement(child, undefined, spinner, child.props.children)
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
        data-loading={loading ? "true" : undefined}
        data-size={size}
        data-variant={variant}
        aria-busy={loading || undefined}
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
      data-loading={loading ? "true" : undefined}
      data-size={size}
      data-variant={variant}
      aria-busy={loading || undefined}
      disabled={isDisabled}
      type={type}
      {...props}
    >
      {spinner}
      {children}
    </button>
  );
}
