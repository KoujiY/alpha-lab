import { useState } from "react";
import type { ReactNode } from "react";

import { useGlossary } from "@/hooks/useGlossary";

interface TermTooltipProps {
  term: string;
  children: ReactNode;
}

export function TermTooltip({ term, children }: TermTooltipProps) {
  const { data } = useGlossary();
  const [open, setOpen] = useState(false);
  const entry = data?.[term];

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <abbr
        title={entry?.short ?? term}
        className="underline decoration-dotted decoration-2 decoration-sky-400 underline-offset-4 cursor-help"
        tabIndex={0}
      >
        {children}
      </abbr>
      {open && entry ? (
        <span
          role="tooltip"
          className="absolute z-10 bottom-full left-0 mb-2 w-64 bg-slate-800 text-slate-100 text-xs p-2 rounded border border-slate-600 shadow-lg"
        >
          <strong className="block mb-1">{entry.term}</strong>
          <span>{entry.short}</span>
        </span>
      ) : null}
    </span>
  );
}
