import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { StockPage } from "@/pages/StockPage";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/stocks/:symbol" element={<StockPage />} />
      </Route>
    </Routes>
  );
}

export default App;
