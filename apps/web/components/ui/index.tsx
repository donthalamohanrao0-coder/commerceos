"use client";

import clsx from "clsx";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

/* ------------------------------------------------------------------ Button */

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
}

const buttonBase =
  "inline-flex items-center justify-center gap-2 rounded-[var(--radius-input)] px-4 py-2 text-sm font-medium " +
  "transition-[background-color,box-shadow,transform,opacity] duration-150 ease-out active:translate-y-px " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-info)] " +
  "disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:active:translate-y-0";

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-primary)] text-[var(--color-primary-fg)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] hover:opacity-95",
  secondary:
    "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-fg)] shadow-[var(--shadow-xs)] hover:bg-[var(--color-surface-muted)] hover:shadow-[var(--shadow-sm)]",
  danger:
    "bg-[var(--color-danger)] text-white shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] hover:opacity-95",
  ghost: "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)]",
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(buttonBase, buttonVariants[variant], className)}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading && <Spinner className="size-4" />}
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ Badge */

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-[var(--color-surface-muted)] text-[var(--color-fg-muted)]",
  success: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)]",
  danger: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
  info: "bg-[var(--color-info-bg)] text-[var(--color-info)]",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        badgeTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ Card */

export function Card({
  children,
  className,
  elevated = false,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  elevated?: boolean;
  as?: "div" | "section" | "article" | "li";
}) {
  return (
    <Tag
      className={clsx(
        "rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)]",
        elevated ? "shadow-[var(--shadow-md)]" : "shadow-[var(--shadow-xs)]",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

/* ------------------------------------------------------------------ Input */

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Field({ label, error, id, className, ...rest }: FieldProps) {
  const fieldId = id ?? rest.name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={fieldId} className="text-sm font-medium text-[var(--color-fg)]">
        {label}
      </label>
      <input
        id={fieldId}
        className={clsx(
          "rounded-[var(--radius-input)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm transition-shadow duration-150",
          "placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-info)] focus:shadow-[var(--shadow-focus)] focus:outline-none",
          error && "border-[var(--color-danger)]",
          className,
        )}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
      {error && <p className="text-xs text-[var(--color-danger)]">{error}</p>}
    </div>
  );
}

/* ------------------------------------------------------------------ Spinner */

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={clsx("animate-spin text-current", className ?? "size-5")}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-90"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ States */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx("co-shimmer rounded-[var(--radius-control)]", className)}
      aria-hidden="true"
    />
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] px-6 py-12 text-center">
      <p className="text-sm font-medium text-[var(--color-fg)]">{title}</p>
      <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-[var(--radius-card)] border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-6 py-10 text-center"
    >
      <p className="text-sm font-semibold text-[var(--color-danger)]">{title}</p>
      <p className="max-w-sm text-sm text-[var(--color-fg-muted)]">{description}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-2">
          Try again
        </Button>
      )}
    </div>
  );
}
