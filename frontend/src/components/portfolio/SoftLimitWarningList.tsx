import { AlertTriangle } from "lucide-react";

import type { SoftLimitWarning } from "@/lib/softLimits";

export interface SoftLimitWarningListProps {
  warnings: SoftLimitWarning[];
  className?: string;
}

export function SoftLimitWarningList({
  warnings,
  className,
}: SoftLimitWarningListProps) {
  if (warnings.length === 0) return null;
  return (
    <ul
      className={
        "space-y-1 rounded border border-amber-700/60 bg-amber-500/10 p-2 text-xs text-amber-200 " +
        (className ?? "")
      }
      data-testid="soft-limit-warnings"
    >
      {warnings.map((w) => (
        <li
          key={w.code}
          className="flex items-start gap-2"
          data-testid={`wizard-warning-${w.code}`}
        >
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          <div>
            <div>{w.message}</div>
            {w.symbols && w.symbols.length > 0 ? (
              <div className="mt-0.5 break-all font-mono text-amber-100/80">
                {w.symbols.join("、")}
              </div>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
