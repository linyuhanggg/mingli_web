"use client";

import { useRef, useState, type FormEvent } from "react";

import {
  submitReadingInput,
  type NeedInputField,
  type NeedInputRequest,
} from "@/lib/api";

import styles from "./need-input-form.module.css";

type FieldValues = Record<string, unknown>;
type FieldErrors = Record<string, string>;

function isBlank(value: unknown): boolean {
  return (
    value === undefined ||
    value === null ||
    (typeof value === "string" && value.trim() === "")
  );
}

function fieldErrorId(fieldId: string): string {
  return `need-input-${fieldId}-error`;
}

function fieldDescriptionId(fieldId: string): string {
  return `need-input-${fieldId}-description`;
}

function coerceValue(field: NeedInputField, value: unknown): unknown {
  if (field.type_id === "integer" && typeof value === "string") {
    return Number.parseInt(value, 10);
  }
  if (
    (field.type_id === "number" || field.type_id === "decimal") &&
    typeof value === "string"
  ) {
    return Number(value);
  }
  return typeof value === "string" ? value.trim() : value;
}

function inputType(field: NeedInputField): React.HTMLInputTypeAttribute {
  switch (field.type_id) {
    case "integer":
    case "number":
    case "decimal":
      return "number";
    case "datetime":
      return "datetime-local";
    case "date":
      return "date";
    default:
      return "text";
  }
}

function fieldStringValue(values: FieldValues, fieldId: string): string {
  const raw = values[fieldId];
  return typeof raw === "string" ? raw : "";
}

export function NeedInputForm({
  readingId,
  request,
  onSubmitted,
}: Readonly<{
  readingId: string;
  request?: NeedInputRequest | null;
  onSubmitted?: () => void;
}>) {
  const [values, setValues] = useState<FieldValues>({});
  const [errors, setErrors] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const busyRef = useRef(false);
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({});

  if (
    !request ||
    !Array.isArray(request.requirements) ||
    request.requirements.length === 0
  ) {
    return (
      <div className={styles.missing} role="alert">
        需要补充资料，但服务端未提供可填写的表单，请稍后重试。
      </div>
    );
  }

  const requirements = request.requirements;

  function setField(fieldId: string, value: unknown) {
    setValues((current) => ({ ...current, [fieldId]: value }));
    const requirement = requirements.find((item) =>
      item.any_of.some((field) => field.id === fieldId),
    );
    setErrors((current) => {
      const next = { ...current };
      for (const field of requirement?.any_of ?? []) {
        delete next[field.id];
      }
      return next;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;

    const nextErrors: FieldErrors = {};
    let firstErrorField = "";
    for (const requirement of requirements) {
      const completedFields = requirement.any_of.filter(
        (field) => !isBlank(values[field.id]),
      );
      if (completedFields.length === 1) {
        continue;
      }
      const message =
        completedFields.length > 1
          ? "本组只能填写一项"
          : requirement.any_of.length === 1
          ? `“${requirement.any_of[0].label}”为必填项`
          : "本组至少填写一项";
      for (const field of requirement.any_of) {
        nextErrors[field.id] = message;
      }
      firstErrorField ||= requirement.any_of[0]?.id ?? "";
    }
    setErrors(nextErrors);
    setSubmitError(null);
    if (firstErrorField) {
      fieldRefs.current[firstErrorField]?.focus();
      return;
    }

    const fields = requirements.flatMap((item) => item.any_of);
    const payload = Object.fromEntries(
      fields
        .filter((field) => !isBlank(values[field.id]))
        .map((field) => [field.id, coerceValue(field, values[field.id])]),
    );

    busyRef.current = true;
    setBusy(true);
    try {
      await submitReadingInput(readingId, payload);
      onSubmitted?.();
    } catch (error) {
      setSubmitError(
        error instanceof Error && error.message
          ? error.message
          : "补充资料提交失败，请稍后重试。",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  return (
    <section className={styles.section} aria-labelledby="need-input-heading">
      <h2 id="need-input-heading" className={styles.heading}>
        补充资料
      </h2>
      <p className={styles.description}>
        服务端需要这些结构化信息后才能继续；输入只会作为 values 提交。
      </p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate aria-busy={busy}>
        <div className={styles.fields}>
          {requirements.map((requirement, requirementIndex) => (
            <fieldset className={styles.requirement} key={`requirement-${requirementIndex}`}>
              {requirement.any_of.length > 1 ? (
                <legend className={styles.requirementLegend}>
                  以下恰好填写一项（必填）
                </legend>
              ) : null}

              {requirement.any_of.map((field, fieldIndex) => {
                const error = errors[field.id];
                const isRequired = requirement.any_of.length === 1;
                const describedBy = [
                  field.description ? fieldDescriptionId(field.id) : "",
                  error ? fieldErrorId(field.id) : "",
                ]
                  .filter(Boolean)
                  .join(" ");
                const common = {
                  disabled: busy,
                  required: isRequired,
                  "aria-required": isRequired ? ("true" as const) : undefined,
                  "aria-invalid": error ? ("true" as const) : undefined,
                  "aria-describedby": describedBy || undefined,
                };

                if (field.type_id === "boolean") {
                  return (
                    <fieldset
                      className={styles.fieldset}
                      key={field.id}
                      aria-invalid={error ? "true" : undefined}
                      aria-describedby={describedBy || undefined}
                    >
                      <legend className={styles.label}>
                        {field.label}
                      </legend>
                      <div className={styles.booleanGroup}>
                        {[
                          { value: true, label: "是" },
                          { value: false, label: "否" },
                        ].map((option, optionIndex) => (
                          <label className={styles.radioLabel} key={option.label}>
                            <input
                              className={styles.radio}
                              type="radio"
                              name={field.id}
                              checked={values[field.id] === option.value}
                              onChange={() => setField(field.id, option.value)}
                              disabled={busy}
                              required={isRequired}
                              ref={(element) => {
                                if (optionIndex === 0) fieldRefs.current[field.id] = element;
                              }}
                            />
                            {option.label}
                          </label>
                        ))}
                      </div>
                      {field.description ? (
                        <p className={styles.help} id={fieldDescriptionId(field.id)}>
                          {field.description}
                        </p>
                      ) : null}
                      {error ? (
                        <p className={styles.fieldError} id={fieldErrorId(field.id)}>
                          {error}
                        </p>
                      ) : null}
                    </fieldset>
                  );
                }

                if (field.choices.length > 0) {
                  return (
                    <div className={styles.field} key={field.id}>
                      <label className={styles.label} htmlFor={`need-input-${field.id}`}>
                        {field.label}
                      </label>
                      <select
                        className={styles.select}
                        id={`need-input-${field.id}`}
                        name={field.id}
                        value={fieldStringValue(values, field.id)}
                        onChange={(event) => setField(field.id, event.target.value)}
                        ref={(element) => {
                          if (fieldIndex === 0) fieldRefs.current[field.id] = element;
                        }}
                        {...common}
                      >
                        <option value="">请选择</option>
                        {field.choices.map((choice) => (
                          <option key={choice.id} value={choice.id}>
                            {choice.label}
                          </option>
                        ))}
                      </select>
                      {field.description ? (
                        <p className={styles.help} id={fieldDescriptionId(field.id)}>
                          {field.description}
                        </p>
                      ) : null}
                      {error ? (
                        <p className={styles.fieldError} id={fieldErrorId(field.id)}>
                          {error}
                        </p>
                      ) : null}
                    </div>
                  );
                }

                const multiline = ["textarea", "multiline"].includes(field.type_id);
                return (
                  <div className={styles.field} key={field.id}>
                    <label className={styles.label} htmlFor={`need-input-${field.id}`}>
                      {field.label}
                    </label>
                    {multiline ? (
                      <textarea
                        className={styles.textarea}
                        id={`need-input-${field.id}`}
                        name={field.id}
                        rows={3}
                        autoComplete="off"
                        value={fieldStringValue(values, field.id)}
                        onChange={(event) => setField(field.id, event.target.value)}
                        ref={(element) => {
                          if (fieldIndex === 0) fieldRefs.current[field.id] = element;
                        }}
                        {...common}
                      />
                    ) : (
                      <input
                        className={styles.input}
                        id={`need-input-${field.id}`}
                        name={field.id}
                        type={inputType(field)}
                        inputMode={field.type_id === "integer" ? "numeric" : undefined}
                        step={field.type_id === "datetime" ? "1" : undefined}
                        autoComplete="off"
                        value={fieldStringValue(values, field.id)}
                        onChange={(event) => setField(field.id, event.target.value)}
                        ref={(element) => {
                          if (fieldIndex === 0) fieldRefs.current[field.id] = element;
                        }}
                        {...common}
                      />
                    )}
                    {field.description ? (
                      <p className={styles.help} id={fieldDescriptionId(field.id)}>
                        {field.description}
                      </p>
                    ) : null}
                    {error ? (
                      <p className={styles.fieldError} id={fieldErrorId(field.id)}>
                        {error}
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </fieldset>
          ))}
        </div>

        {Object.keys(errors).length > 0 ? (
          <p className={styles.alertText} role="alert" aria-live="polite">
            请补全必填项后再提交。
          </p>
        ) : null}
        {submitError ? (
          <p className={styles.alertText} role="alert" aria-live="polite">
            {submitError}
          </p>
        ) : null}

        <button
          type="submit"
          className={styles.submit}
          disabled={busy}
          aria-busy={busy}
        >
          提交补充资料{busy ? " · 正在提交…" : ""}
        </button>
      </form>
    </section>
  );
}
