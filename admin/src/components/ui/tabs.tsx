"use client";

import { Tabs as TabsPrimitive } from "radix-ui";
import type { ReactNode } from "react";

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
  return (
    <TabsPrimitive.Root value={value} onValueChange={onValueChange}>
      <TabsPrimitive.List className={styles.list} aria-label={ariaLabel}>
        {items.map((item) => (
          <TabsPrimitive.Trigger key={item.value} className={styles.trigger} value={item.value}>
            {item.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {items.map((item) => (
        <TabsPrimitive.Content key={item.value} className={styles.panel} value={item.value} tabIndex={0}>
          {item.panel}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
