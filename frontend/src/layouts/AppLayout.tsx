import { Link, Outlet } from "react-router-dom";

import { HeaderSearch } from "@/components/HeaderSearch";
import { L2Panel } from "@/components/education/L2Panel";
import { L2PanelProvider } from "@/components/education/L2PanelContext";

export function AppLayout() {
  return (
    <L2PanelProvider>
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-xl font-bold">alpha-lab</Link>
            <Link to="/portfolios" className="text-sm text-slate-300 hover:text-sky-300">
              組合推薦
            </Link>
          </div>
          <HeaderSearch />
        </header>
        <main className="p-6">
          <Outlet />
        </main>
        <L2Panel />
      </div>
    </L2PanelProvider>
  );
}
