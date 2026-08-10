"use client";

import { useEffect, useRef } from "react";

import type { WorkspaceFocusDetail } from "@/lib/chart-workspace";

import styles from "./focus-detail-drawer.module.css";

const HEADING_ID = "focus-detail-heading";

/**
 * Focus detail surface for the chart workspace. Renders only server-backed
 * facts, limits, and sources; the empty state is honest copy, never a fake
 * ready panel. Labeled and escapable (close button + Escape).
 */
export function FocusDetailDrawer({
  detail,
  onClose,
}: Readonly<{
  detail: WorkspaceFocusDetail | null;
  onClose: () => void;
}>) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (detail) {
      closeRef.current?.focus();
    }
  }, [detail]);

  useEffect(() => {
    if (!detail) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [detail, onClose]);

  return (
    <section
      className={styles.drawer}
      aria-labelledby={HEADING_ID}
      data-open={Boolean(detail)}
    >
      <header className={styles.header}>
        <h4 className={styles.heading} id={HEADING_ID}>
          聚焦详情
        </h4>
        {detail ? (
          <button
            ref={closeRef}
            type="button"
            className={styles.closeButton}
            aria-label="关闭聚焦详情"
            onClick={onClose}
          >
            关闭
          </button>
        ) : null}
      </header>

      {detail ? (
        <div className={styles.body}>
          <p className={styles.detailTitle}>{detail.title}</p>

          {detail.facts.length > 0 ? (
            <dl className={styles.factList}>
              {detail.facts.map((fact) => (
                <div className={styles.factRow} key={`${fact.label}-${fact.text}`}>
                  <dt className={styles.factLabel}>{fact.label}</dt>
                  <dd className={styles.factText}>{fact.text}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          {detail.proseExcerpt ? (
            <p className={styles.prose}>{detail.proseExcerpt}</p>
          ) : null}

          {detail.limits.length > 0 ? (
            <div className={styles.limits}>
              <h5>边界</h5>
              <ul>
                {detail.limits.map((limit) => (
                  <li key={limit}>{limit}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {detail.sources.length > 0 ? (
            <div className={styles.sources}>
              <h5>来源</h5>
              <ul>
                {detail.sources.map((source) => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <p className={styles.empty}>
          选择一个柱位后，这里只显示服务端已公开的聚焦事实。
        </p>
      )}
    </section>
  );
}
