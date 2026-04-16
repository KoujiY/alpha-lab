import { Link } from "react-router-dom";

import type { ReportMeta } from "@/api/types";

const TYPE_BADGE: Record<ReportMeta["type"], { label: string; className: string }> = {
  stock: { label: "個股", className: "bg-sky-500/20 text-sky-300" },
  portfolio: { label: "組合", className: "bg-indigo-500/20 text-indigo-300" },
  events: { label: "事件", className: "bg-amber-500/20 text-amber-300" },
  research: { label: "研究", className: "bg-emerald-500/20 text-emerald-300" },
};

export interface ReportCardProps {
  meta: ReportMeta;
}

export function ReportCard({ meta }: ReportCardProps) {
  const badge = TYPE_BADGE[meta.type];
  return (
    <li className="rounded border border-slate-800 bg-slate-900/60 p-4 hover:border-slate-600">
      <Link to={`/reports/${encodeURIComponent(meta.id)}`} className="block space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded px-2 py-0.5 ${badge.className}`}>{badge.label}</span>
          <span className="text-slate-500">{meta.date}</span>
          {meta.symbols.length > 0 ? (
            <span className="text-slate-400">{meta.symbols.join(", ")}</span>
          ) : null}
        </div>
        <h3 className="text-base font-semibold text-slate-100">{meta.title}</h3>
        {meta.summary_line ? (
          <p className="text-sm text-slate-400">{meta.summary_line}</p>
        ) : null}
        {meta.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1 text-xs text-slate-500">
            {meta.tags.map((tag) => (
              <span key={tag} className="rounded bg-slate-800 px-2 py-0.5">
                #{tag}
              </span>
            ))}
          </div>
        ) : null}
      </Link>
    </li>
  );
}
