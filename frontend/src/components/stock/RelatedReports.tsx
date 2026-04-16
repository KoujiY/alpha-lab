import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listReports } from "@/api/reports";

interface RelatedReportsProps {
  symbol: string;
}

export function RelatedReports({ symbol }: RelatedReportsProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["related-reports", symbol],
    queryFn: () => listReports({ symbol }),
  });

  if (isLoading) return null;

  const items = data ?? [];
  if (items.length === 0) {
    return (
      <section
        className="rounded border border-slate-800 bg-slate-900/40 p-4"
        data-testid="related-reports"
      >
        <h2 className="mb-2 text-sm font-semibold text-slate-300">
          相關分析報告
        </h2>
        <p className="text-xs text-slate-500">尚無相關報告</p>
      </section>
    );
  }
  return (
    <section
      className="rounded border border-slate-800 bg-slate-900/40 p-4"
      data-testid="related-reports"
    >
      <h2 className="mb-2 text-sm font-semibold text-slate-300">
        相關分析報告
      </h2>
      <ul className="space-y-1">
        {items.map((r) => (
          <li key={r.id}>
            <Link
              to={`/reports/${r.id}`}
              className="text-sm text-sky-300 hover:underline"
            >
              {r.starred ? "★ " : ""}
              {r.title}
            </Link>
            <span className="ml-2 text-xs text-slate-500">{r.date}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
