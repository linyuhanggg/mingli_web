"use client";

import type { ReactNode } from "react";

import { motion } from "motion/react";
import { useSyncExternalStore } from "react";

import {
  easeOutExpo,
  motionDurations,
  useSafeReducedMotion,
} from "./motion-primitives";

function subscribeToMount() {
  return () => undefined;
}

function getClientMounted() {
  return true;
}

function getServerMounted() {
  return false;
}

function useHydratedReducedMotion() {
  const mounted = useSyncExternalStore(subscribeToMount, getClientMounted, getServerMounted);
  const reduceMotion = useSafeReducedMotion();
  return mounted && reduceMotion;
}

export function HomeHeroMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduceMotion = useHydratedReducedMotion();

  if (reduceMotion) return <div className={className}>{children}</div>;

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="shown"
      variants={{ shown: { transition: { staggerChildren: 0.06 } }, hidden: {} }}
    >
      {children}
    </motion.div>
  );
}

export function HomeHeroItemMotion({ children }: { children: ReactNode }) {
  const reduceMotion = useHydratedReducedMotion();

  if (reduceMotion) return <div>{children}</div>;

  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 12 }, shown: { opacity: 1, y: 0 } }}
      transition={{ duration: motionDurations.entrance, ease: easeOutExpo }}
    >
      {children}
    </motion.div>
  );
}

export function HomeSectionMotion({
  children,
  className,
  delay = 0,
  dividerClassName,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  dividerClassName?: string;
}) {
  const reduceMotion = useHydratedReducedMotion();

  if (reduceMotion) {
    return (
      <div className={className}>
        {dividerClassName ? <span aria-hidden="true" className={dividerClassName} /> : null}
        {children}
      </div>
    );
  }

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.2 }}
    >
      {dividerClassName ? (
        <motion.span
          aria-hidden="true"
          className={dividerClassName}
          variants={{ hidden: { scaleX: 0 }, shown: { scaleX: 1 } }}
          transition={{ duration: 0.5, delay, ease: easeOutExpo }}
        />
      ) : null}
      <motion.div
        variants={{ hidden: { opacity: 0, y: 12 }, shown: { opacity: 1, y: 0 } }}
        transition={{ duration: motionDurations.entrance, delay, ease: easeOutExpo }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

export function HomeTaskGridMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduceMotion = useHydratedReducedMotion();

  if (reduceMotion) return <div className={className}>{children}</div>;

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.2 }}
      variants={{
        shown: { transition: { staggerChildren: 0.06, delayChildren: 0.06 } },
        hidden: {},
      }}
    >
      {children}
    </motion.div>
  );
}

export function HomeTaskItemMotion({ children }: { children: ReactNode }) {
  return <HomeHeroItemMotion>{children}</HomeHeroItemMotion>;
}

export function HomeLedgerMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <HomeTaskGridMotion className={className}>{children}</HomeTaskGridMotion>;
}

export function HomeLedgerItemMotion({ children }: { children: ReactNode }) {
  const reduceMotion = useHydratedReducedMotion();
  if (reduceMotion) return <article>{children}</article>;
  return (
    <motion.article
      variants={{ hidden: { opacity: 0, y: 12 }, shown: { opacity: 1, y: 0 } }}
      transition={{ duration: motionDurations.entrance, ease: easeOutExpo }}
    >
      {children}
    </motion.article>
  );
}

export function HomeStepsMotion({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduceMotion = useHydratedReducedMotion();
  if (reduceMotion) return <ol className={className}>{children}</ol>;
  return (
    <motion.ol
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.2 }}
      variants={{ shown: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } }, hidden: {} }}
    >
      {children}
    </motion.ol>
  );
}

export function HomeStepItemMotion({ children }: { children: ReactNode }) {
  const reduceMotion = useHydratedReducedMotion();
  if (reduceMotion) return <li>{children}</li>;
  return (
    <motion.li
      variants={{ hidden: { opacity: 0, y: 12 }, shown: { opacity: 1, y: 0 } }}
      transition={{ duration: motionDurations.entrance, ease: easeOutExpo }}
    >
      {children}
    </motion.li>
  );
}
