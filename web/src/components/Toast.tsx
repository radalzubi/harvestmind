"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";

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

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div
        style={{
          position: "fixed",
          bottom: 20,
          right: 20,
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
