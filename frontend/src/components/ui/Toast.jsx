"use client";
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const TONES = {
  success: "border-success-200 bg-success-50 text-success-700",
  error: "border-danger-200 bg-danger-50 text-danger-700",
  warning: "border-warning-200 bg-warning-50 text-warning-700",
  info: "border-info-200 bg-info-50 text-info-700",
};

let idSeq = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (message, { type = "info", duration = 4500 } = {}) => {
      const id = ++idSeq;
      setToasts((prev) => [...prev, { id, message, type }]);
      if (duration) setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ notify, dismiss }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || Info;
          return (
            <div
              key={t.id}
              role="status"
              className={`animate-slide-up flex items-start gap-2.5 rounded-lg border px-4 py-3 text-sm shadow-popover ${TONES[t.type]}`}
            >
              <Icon size={18} className="mt-0.5 shrink-0" />
              <p className="flex-1 leading-snug">{t.message}</p>
              <button
                onClick={() => dismiss(t.id)}
                aria-label="Fechar notificação"
                className="shrink-0 opacity-60 hover:opacity-100"
              >
                <X size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast deve ser usado dentro de <ToastProvider>");
  return ctx;
}
