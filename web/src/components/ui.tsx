"use client";

import React, { ReactNode } from "react";
import clsx from "clsx";

export type RiskKind = "low" | "medium" | "high" | "critical" | "neutral" | "info" | "brand";

export function Badge({
  kind = "neutral",
  children,
  dot = true,
}: {
  kind?: RiskKind;
  children: ReactNode;
  dot?: boolean;
}) {
  return (
    <span className={clsx("badge", kind)}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

export function RiskBadge({ level }: { level?: string | null }) {
  const k = (level || "").toLowerCase() as RiskKind;
  const known: RiskKind[] = ["low", "medium", "high", "critical"];
  return <Badge kind={known.includes(k) ? k : "neutral"}>{level || "n/a"}</Badge>;
}

export function Tbtn({
  children,
  variant = "default",
  icon,
  onClick,
  type = "button",
  disabled,
  pending,
  title,
}: {
  children?: ReactNode;
  variant?: "default" | "primary" | "brand" | "ghost";
  icon?: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  pending?: boolean;
  title?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || pending}
      title={title}
      className={clsx("tbtn", variant !== "default" && variant)}
      style={{
        opacity: disabled || pending ? 0.6 : 1,
        cursor: disabled || pending ? "default" : "pointer",
      }}
    >
      {pending ? (
        <span
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            border: "1.5px solid currentColor",
            borderTopColor: "transparent",
            animation: "spin 0.8s linear infinite",
            display: "inline-block",
          }}
        />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}

export function Card({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return <div className={clsx("card", className)} style={style}>{children}</div>;
}

export function CardHead({
  title,
  sub,
  bordered = false,
  actions,
}: {
  title: string;
  sub?: string;
  bordered?: boolean;
  actions?: ReactNode;
}) {
  return (
    <div className={clsx("card-head card-headrow", bordered && "bordered")}>
      <div>
        <h3>{title}</h3>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {actions && <div className="card-actions">{actions}</div>}
    </div>
  );
}

export function CardBody({
  children,
  tight = false,
  className,
}: {
  children: ReactNode;
  tight?: boolean;
  className?: string;
}) {
  return (
    <div className={clsx("card-body", tight && "tight", className)}>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  sub,
  actions,
}: {
  title: string;
  sub?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {sub && <div className="page-sub">{sub}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function KPI({
  label,
  value,
  unit,
  delta,
  deltaDir = "flat",
  sub,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  delta?: string;
  deltaDir?: "up" | "down" | "flat";
  sub?: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {(delta || sub) && (
        <div className="kpi-meta">
          {delta && (
            <span className={clsx("delta", deltaDir)}>
              {deltaDir === "up" ? "↑" : deltaDir === "down" ? "↓" : "·"} {delta}
            </span>
          )}
          {sub && <span className="kpi-sub">{sub}</span>}
        </div>
      )}
    </div>
  );
}

export function KPIRow({
  cols = 4,
  children,
}: {
  cols?: 3 | 4;
  children: ReactNode;
}) {
  return <div className={clsx("kpi-row", cols === 3 && "cols-3")}>{children}</div>;
}

export function BarCell({
  value,
  max,
  color = "var(--accent)",
  format = (v: number) => `${v}`,
}: {
  value: number;
  max: number;
  color?: string;
  format?: (v: number) => string;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="barcell">
      <div className="bar-bg">
        <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="v">{format(value)}</span>
    </div>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button
          key={t.id}
          className={clsx("tab", value === t.id && "active")}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.count !== undefined && <span className="count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

// ── PageLoading ───────────────────────────────────────────────────────────────

export function PageLoading({ message = "Loading…" }: { message?: string }) {
  return (
    <div className="page">
      <div style={{ color: "var(--muted)", padding: "48px 32px", fontSize: 13 }}>
        <span
          style={{
            display: "inline-block",
            width: 14,
            height: 14,
            borderRadius: "50%",
            border: "1.5px solid var(--muted)",
            borderTopColor: "var(--accent)",
            animation: "spin 0.8s linear infinite",
            marginRight: 10,
            verticalAlign: "middle",
          }}
        />
        {message}
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}

// ── PageError ─────────────────────────────────────────────────────────────────

export function PageError({ error }: { error: string }) {
  const isNetwork =
    error.toLowerCase().includes("fetch") ||
    error.toLowerCase().includes("network") ||
    error.toLowerCase().includes("failed") ||
    error.toLowerCase().includes("refused");

  // Detect whether we're running on localhost (developer's machine) vs. a deployed
  // host (e.g. Vercel). The helper text differs because the right fix is different.
  const isLocalhost =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1");

  return (
    <div className="page">
      <div style={{
        margin: "32px 0",
        padding: "16px 20px",
        border: "1px solid rgba(248,113,113,0.3)",
        background: "rgba(248,113,113,0.06)",
        borderRadius: 8,
        fontSize: 13,
        color: "var(--danger)",
      }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>
          {isNetwork ? "Cannot reach the Zaad Supply API" : "Something went wrong"}
        </div>
        <div style={{ color: "var(--muted)", fontSize: 12 }}>
          {isNetwork
            ? isLocalhost
              ? "The local backend isn't running. Start it with: uvicorn api.main:app --reload"
              : "This deployment is frontend-only, no backend is connected. Run Zaad Supply locally to see live diagnostic data, or contact the team for a demo."
            : error}
        </div>
      </div>
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div style={{
      marginTop: 24,
      padding: "32px 24px",
      border: "1px dashed var(--border)",
      borderRadius: 8,
      textAlign: "center",
      color: "var(--muted)",
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 6 }}>
        {title}
      </div>
      <div style={{ fontSize: 12, lineHeight: 1.6, maxWidth: 420, margin: "0 auto" }}>
        {body}
      </div>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}

// ── InfoBanner ────────────────────────────────────────────────────────────────

export function InfoBanner({
  kind = "warn",
  title,
  children,
}: {
  kind?: "warn" | "info" | "danger";
  title?: string;
  children: ReactNode;
}) {
  const colors = {
    warn: { border: "rgba(251,191,36,0.3)", bg: "rgba(251,191,36,0.06)", text: "var(--warn)" },
    info: { border: "rgba(96,165,250,0.3)", bg: "rgba(96,165,250,0.06)", text: "var(--info, #60a5fa)" },
    danger: { border: "rgba(248,113,113,0.3)", bg: "rgba(248,113,113,0.06)", text: "var(--danger)" },
  }[kind];
  return (
    <div style={{
      marginBottom: 20,
      padding: "12px 16px",
      border: `1px solid ${colors.border}`,
      background: colors.bg,
      borderRadius: 8,
      fontSize: 13,
      display: "flex",
      gap: 10,
      alignItems: "flex-start",
    }}>
      {title && (
        <span style={{ fontWeight: 600, flex: "none", color: colors.text }}>{title}</span>
      )}
      <span style={{ color: "var(--muted)" }}>{children}</span>
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <span className="legend">
      {items.map((i) => (
        <span key={i.label} className="legend-item">
          <span className="legend-swatch" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </span>
  );
}
