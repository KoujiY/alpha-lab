import { useParams } from "react-router-dom";

export function StockPage() {
  const { symbol } = useParams<{ symbol: string }>();
  if (!symbol) {
    return <p className="text-slate-400">找不到股票代號。</p>;
  }
  return (
    <div>
      <h1 className="text-2xl font-bold">個股頁：{symbol}</h1>
      <p className="text-slate-400">Task E3-E6 會把各 section 填上。</p>
    </div>
  );
}
