import type { ButtonHTMLAttributes, ReactNode, SVGProps } from "react";
import { Link, type LinkProps } from "react-router";

export function LogoMark({ className = "size-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9 9.5v5M12 7.5v9M15 9.5v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2 text-[17px] font-bold tracking-tight text-fg">
      <LogoMark />
      Mockwright
    </Link>
  );
}

type Variant = "primary" | "secondary" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-[background-color,color,transform,opacity] duration-150 ease-out active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100";

const variants: Record<Variant, string> = {
  primary: "bg-pill text-ink hover:bg-white",
  secondary: "bg-panel-2 text-fg border border-line hover:bg-[#222226]",
  ghost: "text-muted hover:text-fg",
};

const sizes = {
  md: "h-11 px-6 text-[15px]",
  lg: "h-[52px] px-7 text-[16px]",
  sm: "h-9 px-4 text-[13px]",
};

export function buttonClass(variant: Variant = "primary", size: keyof typeof sizes = "md", extra = "") {
  return `${base} ${variants[variant]} ${sizes[size]} ${extra}`;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: keyof typeof sizes;
  loading?: boolean;
}

export function Button({ variant = "primary", size = "md", loading, className = "", children, disabled, ...rest }: ButtonProps) {
  return (
    <button className={buttonClass(variant, size, className)} disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading && <Spinner className="size-4" />}
      {children}
    </button>
  );
}

interface LinkButtonProps extends LinkProps {
  variant?: Variant;
  size?: keyof typeof sizes;
}

export function LinkButton({ variant = "primary", size = "md", className = "", ...rest }: LinkButtonProps) {
  return <Link className={buttonClass(variant, size, className)} {...rest} />;
}

export function Spinner({ className = "size-5" }: { className?: string }) {
  return <span className={`spinner inline-block rounded-full border-2 border-current border-t-transparent ${className}`} aria-hidden="true" />;
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-[14px] text-[#ffb3b3]">
      {children}
    </p>
  );
}

type IconProps = SVGProps<SVGSVGElement>;

const iconBase = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export const Icon = {
  Mic: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />
    </svg>
  ),
  Stop: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
      <rect x="7" y="7" width="10" height="10" rx="2" />
    </svg>
  ),
  Speaker: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <path d="M4 9.5h3l4-3.5v12l-4-3.5H4z" />
      <path d="M15 9.5a3.5 3.5 0 0 1 0 5M17.5 7a7 7 0 0 1 0 10" />
    </svg>
  ),
  Keyboard: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <rect x="3" y="6" width="18" height="12" rx="2.5" />
      <path d="M7 10h.01M11 10h.01M15 10h.01M8 14h8" />
    </svg>
  ),
  Transcript: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M8 9h8M8 12.5h8M8 16h5" />
    </svg>
  ),
  Chevron: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  ),
  Pause: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
      <rect x="7" y="6" width="3.2" height="12" rx="1" />
      <rect x="13.8" y="6" width="3.2" height="12" rx="1" />
    </svg>
  ),
  Eye: (p: IconProps) => (
    <svg viewBox="0 0 24 24" {...iconBase} {...p}>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
};
