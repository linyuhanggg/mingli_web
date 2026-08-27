"use client";

import clsx from "clsx";
import {
  motion,
  useAnimationControls,
  useIsomorphicLayoutEffect,
  useReducedMotion,
} from "motion/react";
import type { ReactNode } from "react";

export const easeOutExpo = [0.16, 1, 0.3, 1] as const;

export const motionDurations = {
  feedback: 0.12,
  state: 0.22,
  entrance: 0.42,
  focal: 0.42,
} as const;

function isTestRuntime() {
  return (
    process.env.NODE_ENV === "test" ||
    process.env.VITEST === "true" ||
    process.env.VITEST_WORKER_ID !== undefined
  );
}

export function useSafeReducedMotion() {
  return Boolean(useReducedMotion()) || isTestRuntime();
}

function canObserveViewport() {
  return typeof window !== "undefined" && "IntersectionObserver" in window;
}

type RevealProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
  as?: "div" | "section" | "article";
  /** When true, animate on mount instead of whileInView (hero / above fold). */
  immediate?: boolean;
};

export function Reveal({
  children,
  className,
  delay = 0,
  y = 10,
  as = "div",
  immediate = false,
}: RevealProps) {
  const reduceMotion = useSafeReducedMotion();
  const Component =
    as === "section" ? motion.section : as === "article" ? motion.article : motion.div;

  const transition = {
    duration: motionDurations.entrance,
    delay,
    ease: easeOutExpo,
  };

  if (reduceMotion) {
    return <Component className={className}>{children}</Component>;
  }

  const useMount = immediate || !canObserveViewport();

  if (useMount) {
    return (
      <Component
        className={className}
        initial={{ opacity: 0, y }}
        animate={{ opacity: 1, y: 0 }}
        transition={transition}
      >
        {children}
      </Component>
    );
  }

  return (
    <Component
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2, margin: "0px 0px -6% 0px" }}
      transition={transition}
    >
      {children}
    </Component>
  );
}

type StaggerProps = {
  children: ReactNode;
  className?: string;
  stagger?: number;
  delayChildren?: number;
  as?: "div" | "section" | "ol" | "ul";
  immediate?: boolean;
};

export function Stagger({
  children,
  className,
  stagger = 0.07,
  delayChildren = 0.04,
  as = "div",
  immediate = false,
}: StaggerProps) {
  const reduceMotion = useSafeReducedMotion();
  const Component =
    as === "section"
      ? motion.section
      : as === "ol"
        ? motion.ol
        : as === "ul"
          ? motion.ul
          : motion.div;
  const cappedStagger = Math.min(Math.max(stagger, 0.04), 0.09);

  if (reduceMotion) {
    return <Component className={className}>{children}</Component>;
  }

  const variants = {
    hidden: {},
    shown: {
      transition: {
        staggerChildren: cappedStagger,
        delayChildren,
      },
    },
  } as const;

  const useMount = immediate || !canObserveViewport();

  if (useMount) {
    return (
      <Component
        className={className}
        initial="hidden"
        animate="shown"
        variants={variants}
      >
        {children}
      </Component>
    );
  }

  return (
    <Component
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.18 }}
      variants={variants}
    >
      {children}
    </Component>
  );
}

type StaggerItemProps = {
  children: ReactNode;
  className?: string;
  y?: number;
  as?: "div" | "li" | "article";
};

export function StaggerItem({
  children,
  className,
  y = 12,
  as = "div",
}: StaggerItemProps) {
  const shared = {
    className: clsx(className),
    variants: {
      hidden: { opacity: 0, y },
      shown: { opacity: 1, y: 0 },
    },
    transition: { duration: motionDurations.entrance, ease: easeOutExpo },
  } as const;

  if (as === "li") {
    return <motion.li {...shared}>{children}</motion.li>;
  }
  if (as === "article") {
    return <motion.article {...shared}>{children}</motion.article>;
  }
  return <motion.div {...shared}>{children}</motion.div>;
}

type RouteEnterProps = {
  children: ReactNode;
  className?: string;
  routeKey: string;
};

export function RouteEnter({ children, className, routeKey }: RouteEnterProps) {
  const reduceMotion = useSafeReducedMotion();
  const controls = useAnimationControls();

  useIsomorphicLayoutEffect(() => {
    controls.stop();

    if (reduceMotion) {
      controls.set({ opacity: 1, y: 0 });
      return;
    }

    controls.set({ opacity: 0, y: 8 });
    void controls.start({
      opacity: 1,
      y: 0,
      transition: { duration: motionDurations.state, ease: easeOutExpo },
    });

    return () => controls.stop();
  }, [controls, reduceMotion, routeKey]);

  return (
    <motion.div
      key={routeKey}
      className={className}
      initial={false}
      animate={controls}
      style={{ opacity: 1, transform: "none" }}
    >
      {children}
    </motion.div>
  );
}
