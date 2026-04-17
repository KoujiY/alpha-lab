import type { ReportMeta } from "@/api/types";
import { ReportCard } from "@/components/reports/ReportCard";
import { groupReportsByMonth } from "@/lib/reportTimeline";

export interface ReportTimelineProps {
  reports: ReportMeta[];
  onToggleStar?: (id: string, nextStarred: boolean) => void;
  onDelete?: (id: string) => void;
}

export function ReportTimeline({
  reports,
  onToggleStar,
  onDelete,
}: ReportTimelineProps) {
  const groups = groupReportsByMonth(reports);
  return (
    <div className="space-y-6" data-testid="reports-timeline">
      {groups.map((g) => (
        <section key={g.month} data-testid={`timeline-month-${g.month}`}>
          <h2 className="sticky top-0 z-10 bg-slate-950 py-2 text-sm font-semibold text-slate-400">
            {g.month}
          </h2>
          <ul className="mt-2 space-y-2">
            {g.items.map((meta) => (
              <ReportCard
                key={meta.id}
                meta={meta}
                onToggleStar={onToggleStar}
                onDelete={onDelete}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
