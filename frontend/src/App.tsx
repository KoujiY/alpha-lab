import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { PortfoliosPage } from "@/pages/PortfoliosPage";
import { StockPage } from "@/pages/StockPage";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/stocks/:symbol" element={<StockPage />} />
        <Route path="/portfolios" element={<PortfoliosPage />} />
      </Route>
    </Routes>
  );
}

export default App;
