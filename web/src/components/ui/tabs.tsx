"use client";

import { motion } from "motion/react";
import { Tabs as TabsPrimitive } from "radix-ui";
import { useId, useState, type ReactNode } from "react";

import {
  easeOutExpo,
  indicatorSpring,
  motionDurations,
  useSafeReducedMotion,
} from "@/components/motion-primitives";

import styles from "./tabs.module.css";


export type TabItem = {
  value: string;
  label: string;
  panel: ReactNode;
};

export type TabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  items: TabItem[];
  "aria-label": string;
};

export function Tabs({ value, onValueChange, items, "aria-label": ariaLabel }: TabsProps) {
  const indicatorId = useId();
  const reduceMotion = useSafeReducedMotion();
  const [direction, setDirection] = useState<1 | -1>(1);
  const [hasValueChanged, setHasValueChanged] = useState(false);

  function handleValueChange(nextValue: string) {
    if (nextValue === value) return;
    const currentIndex = items.findIndex((item) => item.value === value);
    const nextIndex = items.findIndex((item) => item.value === nextValue);
    setDirection(
      currentIndex >= 0 && nextIndex >= 0 && nextIndex < currentIndex ? -1 : 1,
    );
    setHasValueChanged(true);
    onValueChange(nextValue);
  }

  return (
    <TabsPrimitive.Root value={value} onValueChange={handleValueChange}>
      <TabsPrimitive.List className={styles.list} aria-label={ariaLabel}>
        {items.map((item) => (
          <TabsPrimitive.Trigger key={item.value} className={styles.trigger} value={item.value}>
            {item.label}
            {item.value === value ? (
              <motion.span
                aria-hidden="true"
                className={styles.indicator}
                data-tab-indicator=""
                layoutId={reduceMotion ? undefined : `${indicatorId}-indicator`}
                transition={reduceMotion ? { duration: 0 } : indicatorSpring}
              />
            ) : null}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {items.map((item) => (
        <TabsPrimitive.Content
          key={item.value}
          className={styles.panel}
          data-motion-direction={direction === 1 ? "forward" : "backward"}
          value={item.value}
          tabIndex={0}
        >
          <motion.div
            className={styles.panelMotion}
            initial={
              reduceMotion || !hasValueChanged
                ? false
                : { opacity: 0, x: direction * 8 }
            }
            animate={{ opacity: 1, x: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { duration: motionDurations.content, ease: easeOutExpo }
            }
          >
            {item.panel}
          </motion.div>
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
