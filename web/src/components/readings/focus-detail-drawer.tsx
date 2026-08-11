"use client";

import { useCallback, useEffect, useId, useRef } from "react";

import type { WorkspaceFocusDetail } from "@/lib/chart-workspace";

import styles from "./focus-detail-drawer.module.css";

/**
 * Focus detail surface for the chart workspace. Renders only server-backed
 * facts, limits, and sources; the empty state is honest copy, never a fake
 * ready panel. Labeled and escapable (close button + Escape).
 */
export function FocusDetailDrawer({
  id,
  detail,
  onClose,
}: Readonly<{
  id?: string;
  detail: WorkspaceFocusDetail | null;
  onClose: () => void;
}>) {
  const headingId = useId();
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const detailTitleRef = useRef<HTMLParagraphElement | null>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const handleClose = useCallback(() => {
    const returnTarget = returnFocusRef.current;
    onClose();
    queueMicrotask(() => returnTarget?.focus());
  }, [onClose]);

  useEffect(() => {
    if (detail) {
      const activeElement = document.activeElement;
      if (
        activeElement instanceof HTMLElement &&
        activeElement !== closeRef.current &&
        activeElement !== detailTitleRef.current
      ) {
        returnFocusRef.current = activeElement;
      }
      detailTitleRef.current?.focus();
    }
  }, [detail]);

  useEffect(() => {
    if (!detail) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        handleClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [detail, handleClose]);

  return (
    <section
      id={id}
      className={styles.drawer}
      aria-labelledby={headingId}
      data-open={Boolean(detail)}
    >
      <header className={styles.header}>
        <h4 className={styles.heading} id={headingId}>
          聚焦详情
        </h4>
        {detail ? (
          <button
            ref={closeRef}
            type="button"
            className={styles.closeButton}
            aria-label="关闭聚焦详情"
            onClick={handleClose}
          >
            关闭
          </button>
        ) : null}
      </header>

      {detail ? (
        <div className={styles.body}>
          <p
            ref={detailTitleRef}
            className={styles.detailTitle}
            tabIndex={-1}
          >
            {detail.title}
          </p>

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
