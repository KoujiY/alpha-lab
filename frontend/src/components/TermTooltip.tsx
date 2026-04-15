import { useState } from "react";
import type { ReactNode } from "react";

import { useL2Panel } from "@/components/education/L2PanelContext";
import { useGlossary } from "@/hooks/useGlossary";

interface TermTooltipProps {
  term: string;
  children: ReactNode;
  l2TopicId?: string;
}

export function TermTooltip({ term, children, l2TopicId }: TermTooltipProps) {
  const { data } = useGlossary();
  const [open, setOpen] = useState(false);
  const entry = data?.[term];
  const { openTopic } = useL2Panel();

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
          {l2TopicId ? (
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                openTopic(l2TopicId);
                setOpen(false);
              }}
              className="mt-2 block text-right text-xs text-sky-300 hover:text-sky-200"
            >
              看完整說明 →
            </button>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}
