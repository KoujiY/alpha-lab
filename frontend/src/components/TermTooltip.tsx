import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

import { useL2Panel } from "@/components/education/L2PanelContext";
import { useGlossary } from "@/hooks/useGlossary";

interface TermTooltipProps {
  term: string;
  children: ReactNode;
  l2TopicId?: string;
}

interface TooltipPos {
  top: number;
  left: number;
}

const TOOLTIP_WIDTH = 256; // w-64 = 16rem = 256px
const GAP = 8; // mb-2

export function TermTooltip({ term, children, l2TopicId }: TermTooltipProps) {
  const { data } = useGlossary();
  const [open, setOpen] = useState(false);
  const entry = data?.[term];
  const { openTopic } = useL2Panel();
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const [pos, setPos] = useState<TooltipPos | null>(null);

  useLayoutEffect(() => {
    if (!open || !triggerRef.current) {
      setPos(null);
      return;
    }
    const rect = triggerRef.current.getBoundingClientRect();
    const viewportW =
      typeof window === "undefined" ? TOOLTIP_WIDTH : window.innerWidth;
    let left = rect.left;
    // 保險不讓 tooltip 超出右邊
    if (left + TOOLTIP_WIDTH > viewportW - 8) {
      left = Math.max(8, viewportW - TOOLTIP_WIDTH - 8);
    }
    const top = rect.top - GAP;
    setPos({ top, left });
  }, [open]);

  const tooltip =
    open && entry && pos && typeof document !== "undefined"
      ? createPortal(
          <span
            role="tooltip"
            style={{
              position: "fixed",
              top: pos.top,
              left: pos.left,
              width: TOOLTIP_WIDTH,
              transform: "translateY(-100%)",
              zIndex: 50,
            }}
            className="bg-slate-800 text-slate-100 text-xs p-2 rounded border border-slate-600 shadow-lg"
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
          </span>,
          document.body,
        )
      : null;

  return (
    <span
      ref={triggerRef}
      className="inline-block"
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
      {tooltip}
    </span>
  );
}
