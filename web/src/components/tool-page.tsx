"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { getToolSurface, publicContentSurfaces } from "@/lib/secondary-surfaces";

import { PublicPageShell } from "./public-page-shell";
import styles from "./tool-page.module.css";

const CONNECTED = new Set(["time-check", "chart-similarity", "rhythm", "five-elements"]);

export function ToolsPageFrame({
  title,
  intro,
  backHref,
  backLabel,
  children,
}: {
  readonly title: string;
  readonly intro: string;
  readonly backHref?: string;
  readonly backLabel?: string;
  readonly children: ReactNode;
}) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <div className={styles.column}>
          <header className={styles.header}>
            <h1>{title}</h1>
            <p>{intro}</p>
          </header>
          {children}
          {backHref && backLabel ? (
            <p>
              <Link className={styles.back} href={backHref}>
                {backLabel}
              </Link>
            </p>
          ) : null}
        </div>
      </main>
    </PublicPageShell>
  );
}

export function ToolsIndexView() {
  const entries = publicContentSurfaces.tools.entries ?? [];

  return (
    <ul className={styles.list}>
      {entries.map((entry) => {
        const slug = entry.href.replace("/tools/", "");
        const open = CONNECTED.has(slug);
        return (
          <li key={entry.href}>
            {open ? (
              <Link href={entry.href}>{entry.title}</Link>
            ) : (
              <button className={styles.closed} disabled type="button">
                {entry.title}
              </button>
            )}
            <p>{entry.description}</p>
            {open ? null : <p className={styles.unavailable}>尚未开放</p>}
          </li>
        );
      })}
    </ul>
  );
}

export function ToolBoundaryView({ slug }: { readonly slug: string }) {
  const surface = getToolSurface(slug);
  const form = surface.form;

  if (!form) {
    return (
      <form action="/tools">
        <button className={styles.backButton} type="submit">
          返回工具
        </button>
      </form>
    );
  }

  return (
    <form aria-describedby="tool-boundary-reason" aria-label={`${surface.title}输入`} className={styles.form}>
      {form.fields.map((field) => {
        const hintId = `${field.id}-hint`;
        return (
          <div className={styles.field} key={field.id}>
            <label htmlFor={field.id}>{field.label}</label>
            {field.type === "textarea" ? (
              <textarea
                aria-describedby={hintId}
                aria-readonly="true"
                autoComplete="off"
                id={field.id}
                name={field.id}
                readOnly
                rows={4}
              />
            ) : (
              <input
                aria-describedby={hintId}
                aria-readonly="true"
                autoComplete="off"
                id={field.id}
                name={field.id}
                readOnly
                type="text"
              />
            )}
            <p id={hintId}>{field.hint}</p>
          </div>
        );
      })}
      <button disabled type="submit">
        {form.submitLabel}
      </button>
      <p id="tool-boundary-reason">{form.disabledReason}</p>
    </form>
  );
}
