import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
  useId,
} from "react";
import { cn } from "@/shared/lib/cn";

export interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, hint, error, children, className }: FieldProps) {
  const generatedId = useId();
  const id = htmlFor ?? generatedId;
  return (
    <div className={cn("field", className)}>
      <label className="lab" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint ? (
        <span className="mono text-[0.6rem] tracking-[0.08em] text-ash normal-case">{hint}</span>
      ) : null}
      {error ? <span className="error-text">{error}</span> : null}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn("input", className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn("textarea", className)} {...props} />;
});
