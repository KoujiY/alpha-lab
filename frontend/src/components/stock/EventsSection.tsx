import type { EventPoint } from "@/api/types";

interface EventsSectionProps {
  events: EventPoint[];
}

export function EventsSection({ events }: EventsSectionProps) {
  if (events.length === 0) {
    return (
      <section aria-label="重大訊息">
        <h2 className="text-xl font-semibold mb-3">重大訊息</h2>
        <p className="text-slate-500">尚無重大訊息</p>
      </section>
    );
  }
  return (
    <section aria-label="重大訊息">
      <h2 className="text-xl font-semibold mb-3">重大訊息（近 20 筆）</h2>
      <ul className="space-y-3">
        {events.map((e) => (
          <li key={e.id} className="border border-slate-800 rounded p-3 bg-slate-900">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{new Date(e.event_datetime).toLocaleString("zh-TW")}</span>
              <span>{e.event_type}</span>
            </div>
            <div className="mt-1 font-semibold">{e.title}</div>
            {e.content ? (
              <div className="mt-2 text-sm text-slate-300 whitespace-pre-wrap">
                {e.content}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
