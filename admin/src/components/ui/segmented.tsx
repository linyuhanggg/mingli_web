"use client";

import { useRef, type KeyboardEvent } from "react";

import styles from "./segmented.module.css";


export type SegmentedOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

export type SegmentedProps = {
  value: string;
  onValueChange: (value: string) => void;
  options: SegmentedOption[];
  "aria-label": string;
};

/**
 * A single-select segmented control implementing the WAI-ARIA radio-group
 * pattern with roving tabindex. Arrow keys (Left/Right and Up/Down) plus
 * Home/End both move real focus and select the target, so the checked item is
 * always the focused item.
 */
export function Segmented({
  value,
  onValueChange,
  options,
  "aria-label": ariaLabel,
}: SegmentedProps) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const enabled = options.filter((option) => !option.disabled);
    const current = enabled.findIndex((option) => option.value === value);
    const index = current < 0 ? 0 : current;

    let nextIndex: number;
    if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = enabled.length - 1;
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (index + 1) % enabled.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = (index - 1 + enabled.length) % enabled.length;
    } else {
      return;
    }

    const next = enabled[nextIndex];
    if (!next) return;
    event.preventDefault();
    onValueChange(next.value);
    const targetIndex = options.findIndex((option) => option.value === next.value);
    refs.current[targetIndex]?.focus();
  }

  return (
    <div className={styles.root} role="radiogroup" aria-label={ariaLabel} onKeyDown={onKeyDown}>
      {options.map((option, index) => {
        const checked = option.value === value;
        return (
          <button
            key={option.value}
            ref={(element) => {
              refs.current[index] = element;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            disabled={option.disabled}
            tabIndex={checked && !option.disabled ? 0 : -1}
            className={styles.item}
            onClick={() => {
              if (!option.disabled) onValueChange(option.value);
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
