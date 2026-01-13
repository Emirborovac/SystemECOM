"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastVariant = "info" | "success" | "error";

export type Toast = {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
};

type ToastContextValue = {
  push: (t: Omit<Toast, "id">) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const toast: Toast = { id, ...t };
    setToasts((prev) => [toast, ...prev].slice(0, 4));
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 4500);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 grid gap-2">
      {toasts.map((t) => (
        <div key={t.id} className={`card w-[320px] p-4 ${variantClass(t.variant)}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-medium">{t.title}</div>
              {t.description ? <div className="mt-1 text-xs text-muted">{t.description}</div> : null}
            </div>
            <button className="btn btn-ghost -mt-1 -mr-2 px-2 py-1 text-xs" type="button" onClick={() => onDismiss(t.id)}>
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function variantClass(v: ToastVariant): string {
  if (v === "success") return "border border-[color:var(--accent)]";
  if (v === "error") return "border border-red-500";
  return "border border-border";
}


