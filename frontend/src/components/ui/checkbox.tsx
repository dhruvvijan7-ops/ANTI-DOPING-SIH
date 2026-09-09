import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Checkbox({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        type="checkbox"
        className={cn(
          "h-4 w-4 rounded border-ink-300 text-signal-700 accent-signal-700 focus:ring-2 focus:ring-signal-600 focus:ring-offset-1",
          className,
        )}
        {...props}
      />
    );
  },
);