import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ComponentPropsWithoutRef } from "react";

import { Button, type ButtonVariant } from "@/components/ui";


type ButtonLinkProps = ComponentPropsWithoutRef<typeof Link> & {
  variant?: "primary" | "secondary" | "text";
};

const variantMap: Record<
  NonNullable<ButtonLinkProps["variant"]>,
  Exclude<ButtonVariant, "icon">
> = {
  primary: "primary",
  secondary: "secondary",
  text: "ghost",
};

export function ButtonLink({
  className = "",
  variant = "primary",
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Button asChild className={className} variant={variantMap[variant]}>
      <Link {...props}>
        <span>{children}</span>
        <ArrowUpRight aria-hidden="true" size={17} strokeWidth={1.8} />
      </Link>
    </Button>
  );
}
