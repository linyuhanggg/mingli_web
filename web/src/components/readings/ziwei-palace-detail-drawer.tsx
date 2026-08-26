"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import { useRef } from "react";

import type { ZiweiChartViewModel } from "@/view-models/registry";

import styles from "./ziwei-palace-detail-drawer.module.css";

type Palace = ZiweiChartViewModel["palaces"][number];
type StarRow = NonNullable<Palace["minor_stars"]>[number];
type GodKey = "changsheng12" | "boshi12" | "jiangqian12" | "suiqian12";

const GOD_KEYS: readonly GodKey[] = ["changsheng12", "boshi12", "jiangqian12", "suiqian12"];

export type ZiweiPalaceDetailDrawerProps = {
  palace: Palace | null;
  isLife?: boolean;
  isBody?: boolean;
  brightnessOf: (name: string, branch: string) => string | null;
  huaOf: (name: string, branch: string) => string | null;
  onClose: () => void;
  returnFocusTo?: HTMLElement | null;
};

function text(value: string | null | undefined): string | null {
  const next = value?.trim();
  return next ? next : null;
}

function ganzhi(palace: Palace): string | null {
  if (!palace.heavenly_stem || !palace.earthly_branch) return null;
  return `${palace.heavenly_stem}${palace.earthly_branch}`;
}

function decade(palace: Palace): string | null {
  if (!palace.decadal) return null;
  return `${palace.decadal.age_start}–${palace.decadal.age_end}`;
}

function ages(palace: Palace): string | null {
  const values = palace.ages?.filter((item) => Number.isFinite(item));
  return values?.length ? values.join("、") : null;
}

function starRows(palace: Palace): ReadonlyArray<{ name: string; kind: "major" | "minor" | "adjective"; brightness: string | null; hua: string | null }> {
  const minors = palace.minor_stars ?? [];
  const adjectives = palace.adjective_stars ?? [];
  return [
    ...palace.major_stars.map((name) => ({ name, kind: "major" as const })),
    ...minors.filter((star): star is StarRow & { name: string } => Boolean(star.name)).map((star) => ({
      name: star.name,
      kind: "minor" as const,
      brightness: star.brightness ?? null,
    })),
    ...adjectives.filter((star): star is StarRow & { name: string } => Boolean(star.name)).map((star) => ({
      name: star.name,
      kind: "adjective" as const,
      brightness: star.brightness ?? null,
    })),
  ].map((row) => ({
    name: row.name,
    kind: row.kind,
    brightness: ("brightness" in row ? row.brightness : null) ?? null,
    hua: null,
  }));
}

function gods(palace: Palace): ReadonlyArray<{ key: GodKey; label: string }> {
  return GOD_KEYS.flatMap((key) => {
    const label = text(palace[key]);
    return label ? [{ key, label }] : [];
  });
}

export function ZiweiPalaceDetailDrawer({
  palace,
  isLife = false,
  isBody = false,
  brightnessOf,
  huaOf,
  onClose,
  returnFocusTo = null,
}: ZiweiPalaceDetailDrawerProps) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  if (!palace) return null;

  const name = text(palace.label);
  const stemBranch = ganzhi(palace);
  const decadeText = decade(palace);
  const ageText = ages(palace);
  const stars = starRows(palace).map((row) => ({
    ...row,
    brightness: row.brightness ?? brightnessOf(row.name, palace.earthly_branch),
    hua: huaOf(row.name, palace.earthly_branch),
  }));
  const godRows = gods(palace);

  return (
    <DialogPrimitive.Root
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={styles.overlay} />
        <DialogPrimitive.Content
          className={styles.drawer}
          data-slot="palace-detail"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            returnFocusTo?.focus();
          }}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            closeRef.current?.focus();
          }}
        >
          <header className={styles.header}>
            <DialogPrimitive.Title className={styles.heading}>宫位详情</DialogPrimitive.Title>
            <DialogPrimitive.Description className={styles.srOnly}>
              查看当前宫位的干支、星曜、大限、小限与十二神事实。
            </DialogPrimitive.Description>
            <DialogPrimitive.Close asChild>
              <button aria-label="关闭" className={styles.close} ref={closeRef} type="button">
                关闭
              </button>
            </DialogPrimitive.Close>
          </header>
          <dl className={styles.facts}>
            {name ? (
              <div className={styles.row}>
                <dt>宫</dt>
                <dd>{name}</dd>
              </div>
            ) : null}
            {stemBranch ? (
              <div className={styles.row}>
                <dt>干支</dt>
                <dd>{stemBranch}</dd>
              </div>
            ) : null}
            {isLife || isBody ? (
              <div className={styles.row}>
                <dt>标记</dt>
                <dd>
                  {isLife ? <span className={styles.mark}>命</span> : null}
                  {isBody ? <span className={styles.mark}>身</span> : null}
                </dd>
              </div>
            ) : null}
            {decadeText ? (
              <div className={styles.row}>
                <dt>大限</dt>
                <dd>{decadeText}</dd>
              </div>
            ) : null}
            {ageText ? (
              <div className={styles.row}>
                <dt>小限</dt>
                <dd>{ageText}</dd>
              </div>
            ) : null}
          </dl>
          {stars.length ? (
            <ul aria-label="星曜" className={styles.stars}>
              {stars.map((star) => (
                <li className={styles[star.kind]} key={`${star.kind}-${star.name}`}>
                  {star.name}
                  {star.brightness ? <sup className={styles.brightness}>{star.brightness}</sup> : null}
                  {star.hua ? <span className={styles.hua}>{star.hua}</span> : null}
                </li>
              ))}
            </ul>
          ) : null}
          {godRows.length ? (
            <p aria-label="十二神" className={styles.gods}>
              {godRows.map((god) => (
                <span data-god={god.key} key={god.key}>
                  {god.label}
                </span>
              ))}
            </p>
          ) : null}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
