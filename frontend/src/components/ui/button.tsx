import Link from "next/link";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

/**
 * The platform button.
 *
 * Modelled on the landing-page CTA pair: a solid emerald primary and a
 * hairline glass secondary. Emerald is reserved for the single most important
 * action on a surface — if two buttons in a view are `primary`, one of them is
 * wrong.
 *
 * Renders as `<a>` when `href` is set, `<button>` otherwise, so navigation and
 * actions share one visual language without wrapping.
 */

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "subtle";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  /* solid emerald — one per surface */
  primary:
    "bg-accent text-bg font-semibold hover:bg-accent-hi active:bg-accent-lo " +
    "shadow-[0_1px_0_0_rgba(255,255,255,0.12)_inset,0_6px_18px_-8px_rgba(16,185,129,0.55)] " +
    "disabled:bg-accent/40 disabled:shadow-none",
  /* hairline glass — the default for most actions */
  secondary:
    "border border-border-strong bg-bg-2/50 text-text font-medium " +
    "hover:border-accent/40 hover:bg-surface-2/60 active:bg-surface-2",
  /* quiet — toolbars, icon rows, tertiary actions */
  ghost:
    "text-muted font-medium hover:bg-surface-2/70 hover:text-text active:bg-surface-2",
  /* bordered, no fill — sits between secondary and ghost */
  subtle:
    "border border-border bg-transparent text-muted font-medium " +
    "hover:border-border-strong hover:text-text hover:bg-surface/50",
  /* destructive — confirmations only */
  danger:
    "border border-danger/40 bg-danger/10 text-danger font-medium " +
    "hover:bg-danger/15 hover:border-danger/60"
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 rounded-lg px-3 text-[13px]",
  md: "h-10 gap-2 rounded-xl px-4 text-sm",
  lg: "h-12 gap-2 rounded-xl px-5 text-[15px]"
};

/** Square variants for icon-only buttons, keyed to the same size scale. */
const ICON_SIZES: Record<ButtonSize, string> = {
  sm: "h-8 w-8 rounded-lg",
  md: "h-10 w-10 rounded-xl",
  lg: "h-12 w-12 rounded-xl"
};

const BASE =
  "inline-flex shrink-0 items-center justify-center whitespace-nowrap " +
  "transition-all duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] " +
  "outline-none focus-visible:outline-2 focus-visible:outline-accent/75 focus-visible:outline-offset-2 " +
  "disabled:cursor-not-allowed disabled:opacity-50";

type CommonProps = {
  children?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Leading icon. Pass a sized lucide element, e.g. `<Plus className="h-4 w-4" />`. */
  icon?: ReactNode;
  /** Trailing icon — arrows, chevrons, kbd hints. */
  trailing?: ReactNode;
  /** Swaps the leading icon for a spinner and disables interaction. */
  loading?: boolean;
  /** Square, label-less. Requires `aria-label`. */
  iconOnly?: boolean;
  fullWidth?: boolean;
  className?: string;
};

type ButtonAsButton = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof CommonProps> & {
    href?: undefined;
  };

type ButtonAsLink = CommonProps & {
  href: string;
  /** Opens in a new tab and adds the matching rel. */
  external?: boolean;
  target?: string;
  rel?: string;
  onClick?: () => void;
  "aria-label"?: string;
  title?: string;
};

export type ButtonProps = ButtonAsButton | ButtonAsLink;

export function Button(props: ButtonProps) {
  const {
    children,
    variant = "secondary",
    size = "md",
    icon,
    trailing,
    loading = false,
    iconOnly = false,
    fullWidth = false,
    className = ""
  } = props;

  const cls = [
    BASE,
    VARIANTS[variant],
    iconOnly ? ICON_SIZES[size] : SIZES[size],
    fullWidth ? "w-full" : "",
    className
  ]
    .filter(Boolean)
    .join(" ");

  const spinnerSize = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";

  const content = (
    <>
      {loading ? (
        <Loader2 className={`${spinnerSize} shrink-0 animate-spin`} aria-hidden />
      ) : (
        icon
      )}
      {!iconOnly && children}
      {!loading && trailing}
    </>
  );

  if ("href" in props && props.href !== undefined) {
    const { href, external, target, rel, onClick, title } = props;
    return (
      <Link
        href={href}
        onClick={onClick}
        title={title}
        aria-label={props["aria-label"]}
        target={target ?? (external ? "_blank" : undefined)}
        rel={rel ?? (external ? "noopener noreferrer" : undefined)}
        className={cls}
      >
        {content}
      </Link>
    );
  }

  const {
    children: _c,
    variant: _v,
    size: _s,
    icon: _i,
    trailing: _t,
    loading: _l,
    iconOnly: _io,
    fullWidth: _fw,
    className: _cn,
    disabled,
    type = "button",
    ...rest
  } = props as ButtonAsButton;

  return (
    <button
      {...rest}
      type={type}
      disabled={disabled || loading}
      className={cls}
    >
      {content}
    </button>
  );
}

/**
 * Segmented group — wraps buttons in a single hairline shell with internal
 * dividers. Used for view switchers and pagination clusters.
 */
export function ButtonGroup({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`inline-flex items-center gap-1 rounded-xl border border-border bg-bg-2/50 p-1 ${className}`}
    >
      {children}
    </div>
  );
}
