"use client";

import {
  motion,
  useAnimationControls,
  useIsomorphicLayoutEffect,
} from "motion/react";
import type { ReactNode } from "react";

import {
  easeOutExpo,
  motionDurations,
  useSafeReducedMotion,
} from "@/components/motion-primitives";
import { Button } from "@/components/ui/button";
import { Status } from "@/components/ui/status";

import styles from "./chart-structure-skeleton.module.css";

export type ChartStructureVariant = "bazi" | "ziwei";

const copy: Record<ChartStructureVariant, { title: string; description: string }> = {
  bazi: {
    title: "正在同步八字盘面",
    description: "正在准备定位、时间层与四柱事实；完成后直接进入盘面。",
  },
  ziwei: {
    title: "正在同步紫微盘面",
    description: "正在准备十二宫、中央信息区与时间层事实；完成后直接进入盘面。",
  },
};

export type ChartStructureSkeletonProps = Readonly<{
  canReturn?: boolean;
  onReturn?: () => void;
  variant: ChartStructureVariant;
}>;

export function ChartStructureSkeleton({
  canReturn = false,
  onReturn,
  variant,
}: ChartStructureSkeletonProps) {
  const reduceMotion = useSafeReducedMotion();
  const definition = copy[variant];

  return (
    <motion.section
      animate={{ opacity: 1 }}
      className={styles.waiting}
      data-chart-skeleton={variant}
      exit={reduceMotion ? undefined : { opacity: 0 }}
      initial={reduceMotion ? false : { opacity: 0 }}
      transition={{ duration: motionDurations.stateFeedback, ease: easeOutExpo }}
    >
      <div aria-hidden="true" className={styles.structure} data-variant={variant}>
        <span className={styles.timeLayer} />
        {variant === "bazi" ? (
          <>
            <div className={styles.pillars}>
              {Array.from({ length: 4 }, (_, index) => (
                <span key={index} />
              ))}
            </div>
            <span className={styles.reading} />
          </>
        ) : (
          <div className={styles.ziweiBoard}>
            <ol className={styles.palaces}>
              {Array.from({ length: 12 }, (_, index) => (
                <li key={index} />
              ))}
            </ol>
            <span className={styles.center} />
          </div>
        )}
      </div>
      <Status
        actions={canReturn && onReturn ? (
          <Button onClick={onReturn} variant="secondary">
            返回录入
          </Button>
        ) : null}
        description={definition.description}
        state="processing"
        title={definition.title}
      />
    </motion.section>
  );
}

export function ChartReadyReveal({ children }: Readonly<{ children: ReactNode }>) {
  const reduceMotion = useSafeReducedMotion();
  const controls = useAnimationControls();

  useIsomorphicLayoutEffect(() => {
    controls.stop();
    if (reduceMotion) {
      controls.set({ opacity: 1 });
      return;
    }
    controls.set({ opacity: 0 });
    void controls.start({
      opacity: 1,
      transition: { duration: motionDurations.content, ease: easeOutExpo },
    });
    return () => controls.stop();
  }, [controls, reduceMotion]);

  return (
    <motion.div
      animate={controls}
      data-chart-ready-reveal="true"
      initial={false}
      style={{ opacity: 1 }}
    >
      {children}
    </motion.div>
  );
}
