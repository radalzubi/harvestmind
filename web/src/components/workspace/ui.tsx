"use client";

/**
 * The workspace primitives. One button hierarchy, one disclosure pattern, one way to
 * render a fact that may not exist, one empty/loading/error vocabulary. Pages compose
 * these; no page defines its own control styling.
 */
import { forwardRef, type ReactNode } from "react";
import Link from "next/link";
import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import type { EvidenceItem, Fact } from "@/lib/zaad/decisions";

export type ButtonRole = "primary" | "brand" | "secondary" | "tertiary" | "danger";
export type ButtonSize = "sm" | "md" | "lg" | "xl";

function classes(role: ButtonRole, size: ButtonSize, extra?: { pill?: boolean; block?: boolean; icon?: boolean; className?: string }) {
  return clsx("zb", `zb--${role}`, size !== "md" && `zb--${size}`,
    extra?.pill && "zb--pill", extra?.block && "zb--block", extra?.icon && "zb--icon", extra?.className);
}

export const Button = forwardRef<HTMLButtonElement, {
  children?: ReactNode;
  role?: ButtonRole;
  size?: ButtonSize;
  icon?: ReactNode;
  pill?: boolean;
  block?: boolean;
  pending?: boolean;
  disabled?: boolean;
  type?: "button" | "submit";
  onClick?: () => void;
  className?: string;
  /** Required when the button shows only an icon. */
  label?: string;
}>(function Button({ children, role = "secondary", size = "md", icon, pill, block, pending, disabled, type = "button", onClick, className, label }, ref) {
  const iconOnly = !children && Boolean(icon);
  return (
    <button
      ref={ref} type={type} onClick={onClick} disabled={disabled || pending}
      aria-label={label ?? (iconOnly ? undefined : undefined)}
      title={iconOnly ? label : undefined}
      className={classes(role, size, { pill, block, icon: iconOnly, className })}
    >
      {pending ? <span className="phase-spin" style={{ width: 13, height: 13, borderRadius: "50%", border: "1.5px solid currentColor", borderTopColor: "transparent", animation: "spin .8s linear infinite", display: "inline-block" }} /> : icon}
      {children}
    </button>
  );
});

export function ButtonLink({ href, children, role = "secondary", size = "md", icon, pill, block, className, prefetch }: {
  href: string; children?: ReactNode; role?: ButtonRole; size?: ButtonSize; icon?: ReactNode;
  pill?: boolean; block?: boolean; className?: string; prefetch?: boolean;
}) {
  return (
    <Link href={href} prefetch={prefetch} className={classes(role, size, { pill, block, icon: !children && Boolean(icon), className })}>
      {icon}{children}
    </Link>
  );
}

/** A page's one heading, its one sentence and its one primary action. */
export function PageHead({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  return (
    <header className="ws-h">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {actions && <div className="ws-h-actions">{actions}</div>}
    </header>
  );
}

export function Section({ title, more, moreHref, children }: { title: string; more?: string; moreHref?: string; children: ReactNode }) {
  return (
    <section className="ws-sec">
      <div className="ws-sec-h">
        <h2>{title}</h2>
        {more && moreHref && <Link className="more" href={moreHref}>{more}</Link>}
      </div>
      {children}
    </section>
  );
}

/**
 * One level of disclosure. `hint` says what is behind it so nobody has to open it to find out.
 * Level 1 is always the page itself; this is level 2 and level 3.
 */
export function Disclosure({ summary, hint, children, defaultOpen }: { summary: string; hint?: string; children: ReactNode; defaultOpen?: boolean }) {
  return (
    <details className="disc" open={defaultOpen}>
      <summary>
        <ChevronRight size={14} className="chev" aria-hidden />
        {summary}
        {hint && <span className="hint">{hint}</span>}
      </summary>
      <div className="disc-body">{children}</div>
    </details>
  );
}

/** Raw report fragments, for an analyst. Never on the default path. */
export function TechnicalDetails({ value, hint }: { value: unknown; hint?: string }) {
  return (
    <Disclosure summary="Technical details" hint={hint}>
      <pre className="disc-tech">{JSON.stringify(value, null, 2)}</pre>
    </Disclosure>
  );
}

/** A grid of named quantities. A fact the report did not carry says so rather than showing zero. */
export function Facts({ items }: { items: Fact[] }) {
  const shown = items.filter((f) => f.value !== undefined);
  if (!shown.length) return null;
  return (
    <dl className="facts">
      {shown.map((f) => (
        <div key={f.label}>
          <dt>{f.label}</dt>
          <dd className={f.value == null ? "na" : undefined}>
            {f.value ?? "Not available"}
            {f.note && <span className="note">{f.note}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Evidence({ items }: { items: EvidenceItem[] }) {
  if (!items.length) return <p className="na">No evidence is recorded for this item.</p>;
  return (
    <dl className="evid">
      {items.map((e, i) => (
        <div className="evid-row" key={`${e.label}-${i}`}>
          <dt>{e.label}</dt>
          <dd>
            {e.detail}
            {e.provenance && <span className="evid-prov" title="Where this figure came from">{e.provenance.replaceAll("_", " ").toLowerCase()}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function EmptyState({ title, children, actions }: { title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="state-box">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {actions && <div className="actions">{actions}</div>}
    </div>
  );
}

/** Every error says what happened, what it affects and what the reader can do. */
export function ErrorState({ title, affects, whatToDo, detail, actions }: {
  title: string; affects: string; whatToDo: string; detail?: string; actions?: ReactNode;
}) {
  return (
    <div className="state-box" data-tone="error" role="alert">
      <h3>{title}</h3>
      <p>{affects} {whatToDo}</p>
      {actions && <div className="actions">{actions}</div>}
      {detail && (
        <div style={{ marginTop: 14, textAlign: "start" }}>
          <Disclosure summary="Diagnostics" hint="for support">
            <pre className="disc-tech">{detail}</pre>
          </Disclosure>
        </div>
      )}
    </div>
  );
}

/** Skeletons for an expected load; the label names the call actually in flight. */
export function Loading({ label, cards = 3 }: { label: string; cards?: number }) {
  return (
    <div>
      <p className="phase" aria-live="polite"><span className="spin" aria-hidden />{label}</p>
      <div className="dec-list" style={{ marginTop: 14 }} aria-hidden>
        {Array.from({ length: cards }, (_, i) => <div key={i} className="sk sk-card" />)}
      </div>
    </div>
  );
}

export function Tag({ tone, children }: { tone?: "illustrative" | "live" | "approx"; children: ReactNode }) {
  return <span className="tag" data-tone={tone}>{children}</span>;
}

export function Notice({ tone, children }: { tone?: "warn" | "info"; children: ReactNode }) {
  return <div className="notice" data-tone={tone}>{children}</div>;
}
