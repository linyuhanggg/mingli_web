"use client";

import { useState, type ReactNode } from "react";

import {
  HEPAN_SIX_STATES,
  HepanSixStateSurface,
  type HepanSurfaceState,
} from "@/components/relationship/hepan-six-state-surface";

import styles from "./bazi-result-six-states.module.css";

export function HepanResultSixStates({ children }: { readonly children: ReactNode }) {
  const [state, setState] = useState<"ready" | HepanSurfaceState>("ready");

  return (
    <div className={styles.wrap}>
      <nav aria-label="合盘六态" className={styles.nav}>
        <button
          aria-pressed={state === "ready"}
          className={styles.tab}
          onClick={() => setState("ready")}
          type="button"
        >
          已返回事实
        </button>
        {HEPAN_SIX_STATES.map((item) => (
          <button
            aria-pressed={state === item}
            className={styles.tab}
            key={item}
            onClick={() => setState(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </nav>
      {state === "ready" ? children : <HepanSixStateSurface state={state} />}
    </div>
  );
}
