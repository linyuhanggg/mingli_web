"use client";

import Link from "next/link";
import type { FormEvent } from "react";

import type { AuthSurfaceSpec } from "@/lib/secondary-surfaces";

import { SecondaryStatus } from "./secondary-status";
import { SecondarySurfaceFrame } from "./secondary-surface-frame";
import styles from "./secondary-surfaces.module.css";

export function AuthSurface({ surface }: { readonly surface: AuthSurfaceSpec }) {
  function preventUnavailableSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  const disabledReasonId = `${surface.submitLabel.replaceAll(" ", "-")}-reason`;

  return (
    <SecondarySurfaceFrame eyebrow={surface.eyebrow} intro={surface.intro} title={surface.title}>
      <div className={styles.authGrid}>
        <form
          aria-describedby={disabledReasonId}
          aria-label={`${surface.eyebrow}表单`}
          className={styles.form}
          onSubmit={preventUnavailableSubmit}
        >
          {surface.fields.length ? (
            <div className={styles.fields}>
              {surface.fields.map((field) => {
                const hintId = `${field.id}-hint`;
                return (
                  <div className={styles.field} key={field.id}>
                    <label htmlFor={field.id}>{field.label}</label>
                    <input
                      aria-describedby={hintId}
                      aria-readonly="true"
                      autoComplete={field.autoComplete}
                      id={field.id}
                      name={field.id}
                      readOnly
                      spellCheck={false}
                      type={field.type}
                    />
                    <p id={hintId}>{field.hint}</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.policyPreview}>
              {surface.sections?.map((section) => (
                <section key={section.title}>
                  <h2>{section.title}</h2>
                  <p>{section.description}</p>
                </section>
              ))}
            </div>
          )}

          <button aria-describedby={disabledReasonId} disabled type="submit">
            {surface.submitLabel}
          </button>
          <p className={styles.disabledReason} id={disabledReasonId}>
            身份服务尚未接通，此按钮不会提交任何资料。
          </p>
        </form>

        <aside className={styles.authAside} aria-label="认证状态与其他入口">
          <SecondaryStatus
            description={surface.statusDescription}
            state={surface.state}
            title={surface.statusTitle}
          />
          {surface.links.length ? (
            <nav aria-label="其他认证入口">
              <ul className={styles.linkList}>
                {surface.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
