"use client";

import { ChevronDown, Loader2, Search } from "lucide-react";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes
} from "react";
import { forwardRef } from "react";

/**
 * Form field primitives.
 *
 * One field shell — hairline border, matte fill, emerald focus ring — shared by
 * text, search, select and textarea so no two inputs on the platform disagree
 * about height, radius or focus treatment.
 */

const FIELD =
  "w-full rounded-xl border border-border bg-bg-2/60 text-sm text-text " +
  "outline-none transition-all duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] " +
  "placeholder:text-faint " +
  "hover:border-border-strong " +
  "focus:border-accent/60 focus:bg-surface/60 focus:ring-4 focus:ring-accent/10 " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const SIZES = {
  sm: "h-8 px-2.5 text-[13px]",
  md: "h-10 px-3",
  lg: "h-12 px-4 text-[15px]"
} as const;

export type FieldSize = keyof typeof SIZES;

/* ---------------------------------------------------------------- text input */

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  fieldSize?: FieldSize;
  /** Leading adornment — an icon, rendered inside the field. */
  icon?: ReactNode;
  /** Trailing adornment — a unit, a kbd hint, a clear button. */
  trailing?: ReactNode;
  invalid?: boolean;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { fieldSize = "md", icon, trailing, invalid, className = "", ...rest },
  ref
) {
  const padded = [
    icon ? (fieldSize === "sm" ? "pl-8" : "pl-9") : "",
    trailing ? (fieldSize === "sm" ? "pr-8" : "pr-9") : ""
  ]
    .filter(Boolean)
    .join(" ");

  const field = (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={`${FIELD} ${SIZES[fieldSize]} ${padded} ${
        invalid ? "border-danger/60 focus:border-danger focus:ring-danger/10" : ""
      } ${className}`}
      {...rest}
    />
  );

  if (!icon && !trailing) return field;

  return (
    <div className="relative w-full">
      {icon && (
        <span
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          aria-hidden
        >
          {icon}
        </span>
      )}
      {field}
      {trailing && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted">
          {trailing}
        </span>
      )}
    </div>
  );
});

/* -------------------------------------------------------------- search input */

/**
 * Search field with a leading magnifier that becomes a spinner while a
 * transition is pending — the pattern already used by list controls.
 */
export const SearchInput = forwardRef<
  HTMLInputElement,
  InputProps & { pending?: boolean }
>(function SearchInput({ pending = false, fieldSize = "md", ...rest }, ref) {
  return (
    <Input
      ref={ref}
      type="search"
      fieldSize={fieldSize}
      icon={
        pending ? (
          <Loader2 className="h-4 w-4 animate-spin text-accent" />
        ) : (
          <Search className="h-4 w-4" />
        )
      }
      {...rest}
    />
  );
});

/* -------------------------------------------------------------------- select */

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  fieldSize?: FieldSize;
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { fieldSize = "md", className = "", children, ...rest },
  ref
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={`${FIELD} ${SIZES[fieldSize]} cursor-pointer appearance-none pr-9 ${className}`}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
        aria-hidden
      />
    </div>
  );
});

/* ------------------------------------------------------------------ textarea */

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ className = "", rows = 4, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        rows={rows}
        className={`${FIELD} resize-y px-3 py-2.5 leading-relaxed ${className}`}
        {...rest}
      />
    );
  }
);

/* --------------------------------------------------------------------- field */

/**
 * Label + hint + error wrapper. Keeps vertical rhythm consistent across forms
 * and wires `aria-describedby` so hints and errors are announced.
 */
export function Field({
  label,
  hint,
  error,
  htmlFor,
  required,
  children,
  className = ""
}: {
  label: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const describedBy = error
    ? `${htmlFor}-error`
    : hint
      ? `${htmlFor}-hint`
      : undefined;

  return (
    <div className={`space-y-2 ${className}`}>
      <label
        htmlFor={htmlFor}
        className="block text-[13px] font-medium text-text"
      >
        {label}
        {required && <span className="ml-1 text-accent">*</span>}
      </label>
      <div aria-describedby={describedBy}>{children}</div>
      {error ? (
        <p id={`${htmlFor}-error`} className="text-xs text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${htmlFor}-hint`} className="text-xs leading-relaxed text-faint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/* --------------------------------------------------------------------- toggle */

/** Switch control for boolean preferences. */
export function Toggle({
  checked,
  onChange,
  label,
  disabled
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] disabled:cursor-not-allowed disabled:opacity-50 ${
        checked
          ? "border-accent/50 bg-accent/25"
          : "border-border bg-bg-2 hover:border-border-strong"
      }`}
    >
      <span
        className={`absolute h-4 w-4 rounded-full transition-transform duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          checked ? "translate-x-[24px] bg-accent" : "translate-x-[3px] bg-muted"
        }`}
      />
    </button>
  );
}
