import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { PortfoliosPage } from "@/pages/PortfoliosPage";
import { PortfolioTrackingPage } from "@/pages/PortfolioTrackingPage";
import { ReportDetailPage } from "@/pages/ReportDetailPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { ScreenerPage } from "@/pages/ScreenerPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { StockPage } from "@/pages/StockPage";
import { StocksPage } from "@/pages/StocksPage";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/stocks" element={<StocksPage />} />
        <Route path="/stocks/:symbol" element={<StockPage />} />
        <Route path="/portfolios" element={<PortfoliosPage />} />
        <Route path="/portfolios/:id" element={<PortfolioTrackingPage />} />
        <Route path="/screener" element={<ScreenerPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:reportId" element={<ReportDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
