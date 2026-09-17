import { X } from "lucide-react";
import { type ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "@/shared/i18n";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Dialog({ open, onClose, title, children, footer }: DialogProps) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const previous = document.activeElement as HTMLElement | null;
    panelRef.current?.querySelector<HTMLElement>("input, textarea, select, button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div
      className="overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="dialog fade on"
      >
        <div className="dialog-head">
          <h2 className="text-lg font-extrabold tracking-tight">{title}</h2>
          <button type="button" className="sq" onClick={onClose} aria-label={t("common.close")}>
            <X size={15} strokeWidth={2} aria-hidden />
          </button>
        </div>
        {children}
        {footer ? <div className="flex justify-end gap-3">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  children,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: string;
  confirmLabel: string;
  children?: ReactNode;
  pending?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Dialog open={open} onClose={onClose} title={title}>
      {description ? <p className="text-sm text-ash">{description}</p> : null}
      {children}
      <div className="flex justify-end gap-3">
        <button type="button" className="plain" onClick={onClose}>
          {t("common.cancel")}
        </button>
        <button type="button" className="pill" onClick={onConfirm} disabled={pending}>
          {confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}
