import { useHealth } from "@/api/health";

export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return (
      <div className="text-slate-400" role="status">
        檢查後端中...
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-red-400" role="alert">
        ⚠ 後端連線失敗（請確認 backend dev server 是否運行於 :8000）
      </div>
    );
  }

  return (
    <div className="text-emerald-400" role="status">
      ✓ 後端連線正常 · v{data.version}
    </div>
  );
}
