import { Link, Outlet } from "react-router-dom";
import { HeaderSearch } from "@/components/HeaderSearch";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold">alpha-lab</Link>
        <HeaderSearch />
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
