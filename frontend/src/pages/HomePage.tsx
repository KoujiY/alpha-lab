import { HealthStatus } from "@/components/HealthStatus";

export function HomePage() {
  return (
    <div className="text-center space-y-4">
      <h1 className="text-4xl font-bold">alpha-lab</h1>
      <p className="text-slate-400">台股長線投資工具</p>
      <HealthStatus />
      <p className="text-slate-500 text-sm">
        在右上角搜尋框輸入股票代號（例：2330）即可查看個股頁。
      </p>
    </div>
  );
}
