import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { ApiError } from "@/shared/api/client";
import { translateErrorCode, useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";

interface Toast {
  id: number;
  message: string;
  tone: "info" | "error";
}

interface ToastContextValue {
  push: (message: string, tone?: "info" | "error") => void;
  pushError: (error: unknown) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, tone: "info" | "error" = "info") => {
    toastId += 1;
    const id = toastId;
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  const pushError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError) {
        push(translateErrorCode(t, error.code, error.detail), "error");
        return;
      }
      push(t("errors.generic"), "error");
    },
    [push, t],
  );

  const value = useMemo(() => ({ push, pushError }), [push, pushError]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <output key={toast.id} className={cn("toast block", toast.tone === "error" && "error")}>
            {toast.message}
          </output>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast deve ser usado dentro de ToastProvider");
  }
  return context;
}
