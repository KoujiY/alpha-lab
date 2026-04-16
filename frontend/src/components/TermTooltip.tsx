import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

import { useL2Panel } from "@/components/education/L2PanelContext";
import { useTutorialMode } from "@/contexts/TutorialModeContext";
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
const GAP = 8; // 與 trigger 間距

export function TermTooltip({ term, children, l2TopicId }: TermTooltipProps) {
  const { data } = useGlossary();
  const { mode } = useTutorialMode();
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

  // off 模式：完全不顯示教學痕跡，原樣輸出 children
  if (mode === "off") {
    return <>{children}</>;
  }

  const handleOpenL2 = () => {
    if (!l2TopicId) return;
    openTopic(l2TopicId);
    setOpen(false);
  };

  const triggerExtraProps = l2TopicId
    ? {
        role: "button" as const,
        onClick: handleOpenL2,
        onKeyDown: (e: React.KeyboardEvent<HTMLElement>) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleOpenL2();
          }
        },
      }
    : {};

  // compact 模式：保留點擊進 L2 的入口（若 l2TopicId 存在）但不顯示 hover tooltip
  const showTooltip = mode === "full";

  const tooltip =
    showTooltip && open && entry && pos && typeof document !== "undefined"
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
              <span className="mt-2 block text-right text-[11px] text-sky-300">
                點「{entry.term}」查看完整說明
              </span>
            ) : null}
          </span>,
          document.body,
        )
      : null;

  const hoverHandlers = showTooltip
    ? {
        onMouseEnter: () => setOpen(true),
        onMouseLeave: () => setOpen(false),
        onFocus: () => setOpen(true),
        onBlur: () => setOpen(false),
      }
    : {};

  return (
    <span ref={triggerRef} className="inline-block" {...hoverHandlers}>
      <abbr
        title={entry?.short ?? term}
        className={
          l2TopicId
            ? "underline decoration-dotted decoration-2 decoration-sky-400 underline-offset-4 cursor-pointer hover:text-sky-300"
            : "underline decoration-dotted decoration-2 decoration-sky-400 underline-offset-4 cursor-help"
        }
        tabIndex={0}
        {...triggerExtraProps}
      >
        {children}
      </abbr>
      {tooltip}
    </span>
  );
}
