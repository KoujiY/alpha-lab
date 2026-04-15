import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

export function HeaderSearch() {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    navigate(`/stocks/${encodeURIComponent(trimmed)}`);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <label className="sr-only" htmlFor="symbol-search">
        股票代號
      </label>
      <input
        id="symbol-search"
        aria-label="股票代號"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="輸入代號或名稱，例：2330"
        className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-sm w-64"
      />
      <button
        type="submit"
        className="bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded text-sm"
      >
        查詢
      </button>
    </form>
  );
}
