import { cva, type VariantProps } from "class-variance-authority";
import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/shared/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-semibold transition-colors whitespace-nowrap disabled:opacity-45 disabled:cursor-not-allowed",
  {
    variants: {
      variant: {
        primary:
          "min-h-[46px] rounded-full px-5 bg-ink text-paper border border-ink hover:bg-transparent hover:text-ink",
        outline:
          "min-h-[38px] rounded-full px-4 bg-transparent text-ink border border-rule hover:border-ink hover:bg-hover",
        ghost: "min-h-[34px] px-2 text-ash hover:text-ink",
        plain:
          "px-0 min-h-0 border-b border-rule pb-0.5 rounded-none text-ash text-sm hover:text-ink hover:border-ink",
        danger:
          "min-h-[38px] rounded-full px-4 border border-danger text-danger bg-transparent hover:bg-danger hover:text-paper",
      },
      size: {
        sm: "text-xs",
        md: "text-sm",
        lg: "text-base",
        icon: "h-[34px] w-[34px] min-h-0 p-0 rounded-none border border-rule hover:border-ink hover:bg-hover",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
});
