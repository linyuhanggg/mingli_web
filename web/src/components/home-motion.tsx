"use client";

import type { ReactNode } from "react";

import { Reveal, Stagger, StaggerItem } from "./motion-primitives";

export function HomeHeroMotion({ children }: { children: ReactNode }) {
  return (
    <Reveal as="div" immediate y={12} delay={0.02}>
      {children}
    </Reveal>
  );
}

export function HomeSectionMotion({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <Reveal as="div" className={className} delay={delay} y={12}>
      {children}
    </Reveal>
  );
}

export function HomeTaskGridMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <Stagger className={className} stagger={0.07} delayChildren={0.06}>
      {children}
    </Stagger>
  );
}

export function HomeTaskItemMotion({ children }: { children: ReactNode }) {
  return <StaggerItem as="div">{children}</StaggerItem>;
}

export function HomeLedgerMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <Stagger className={className} stagger={0.06} delayChildren={0.05}>
      {children}
    </Stagger>
  );
}

export function HomeLedgerItemMotion({ children }: { children: ReactNode }) {
  return <StaggerItem as="article">{children}</StaggerItem>;
}

export function HomeStepsMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <Stagger as="ol" className={className} stagger={0.06} delayChildren={0.04}>
      {children}
    </Stagger>
  );
}

export function HomeStepItemMotion({ children }: { children: ReactNode }) {
  return <StaggerItem as="li">{children}</StaggerItem>;
}
