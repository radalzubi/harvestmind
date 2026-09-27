"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import { TENANT_RESET_EVENT } from "@/lib/tenant-state";

type ToastKind = "success" | "info" | "warn";
type Toast = { id: number; kind: ToastKind; text: string };

type Ctx = {
  push: (text: string, kind?: ToastKind) => void;
};

const ToastCtx = createContext<Ctx | null>(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be inside <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const push = useCallback((text: string, kind: ToastKind = "success") => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, kind, text }]);
  }, []);

  // a confirmation that names a job or a proposal belongs to the workspace it was shown in (SEC-038)
  useEffect(() => {
    const on = () => setItems([]);
    window.addEventListener(TENANT_RESET_EVENT, on);
    return () => window.removeEventListener(TENANT_RESET_EVENT, on);
  }, []);

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      {/*
        Every confirmation this product gives lands here — "Proposal created", "Approved. Nothing
        has been sent to a supplier", "Format saved" — and without a live region a screen reader
        announced none of them: the action appeared to do nothing. `aria-atomic="false"` so only
        the new message is read, not the whole stack again.

        The inset is logical, so the stack sits in the trailing corner in Arabic as well.
      */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="false"
        style={{
          position: "fixed",
          bottom: 20,
          insetInlineEnd: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          zIndex: 50,
          pointerEvents: "none",
        }}
      >
        {items.map((t) => (
          <ToastCard
            key={t.id}
            toast={t}
            onClose={() => setItems((s) => s.filter((x) => x.id !== t.id))}
          />
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

function ToastCard({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const accent =
    toast.kind === "warn" ? "var(--bad)" : toast.kind === "info" ? "var(--ink-700)" : "var(--good)";

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line)",
        borderLeft: `3px solid ${accent}`,
        borderRadius: "var(--radius)",
        padding: "10px 14px",
        boxShadow: "var(--shadow-md)",
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 13,
        color: "var(--ink-900)",
        minWidth: 240,
        maxWidth: 380,
        pointerEvents: "auto",
      }}
    >
      {toast.kind === "warn" ? (
        <AlertTriangle size={15} color={accent} strokeWidth={1.8} />
      ) : (
        <CheckCircle2 size={15} color={accent} strokeWidth={1.8} />
      )}
      <span style={{ flex: 1 }}>{toast.text}</span>
      <button
        onClick={onClose}
        style={{
          background: "transparent",
          border: 0,
          cursor: "pointer",
          color: "var(--ink-500)",
          padding: 0,
          display: "grid",
          placeItems: "center",
        }}
      >
        <X size={14} strokeWidth={1.6} />
      </button>
    </div>
  );
}
