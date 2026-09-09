import { forwardRef, type TdHTMLAttributes, type ThHTMLAttributes, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Table({ className, children, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full border-collapse text-sm", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function THead({ className, children, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn("border-b border-ink-100 bg-ink-50/60", className)} {...props}>
      {children}
    </thead>
  );
}

export function TBody({ className, children, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-ink-50", className)} {...props}>{children}</tbody>;
}

export function TR({ className, children, ...props }: HTMLAttributes<HTMLTableRowElement> & { onClick?: () => void }) {
  return (
    <tr className={cn("transition-colors", className)} {...props}>
      {children}
    </tr>
  );
}

export const TH = forwardRef<HTMLTableCellElement, ThHTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }>(
  function TH({ className, children, ...props }, ref) {
    return (
      <th
        ref={ref}
        scope="col"
        className={cn(
          "whitespace-nowrap px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-ink-600",
          className,
        )}
        {...props}
      >
        {children}
      </th>
    );
  },
);

export const TD = forwardRef<HTMLTableCellElement, TdHTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }>(
  function TD({ className, children, ...props }, ref) {
    return (
      <td ref={ref} className={cn("px-3 py-2.5 align-middle text-ink-800", className)} {...props}>
        {children}
      </td>
    );
  },
);

export function TableEmpty({
  colSpan,
  children,
}: {
  colSpan: number;
  children?: ReactNode;
}) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-10 text-center text-sm text-ink-500">
        {children ?? "No records to display."}
      </td>
    </tr>
  );
}