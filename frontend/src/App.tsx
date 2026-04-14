import { HealthStatus } from "@/components/HealthStatus";

function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">alpha-lab</h1>
        <p className="text-slate-400">Phase 0 骨架運作中</p>
        <HealthStatus />
      </div>
    </main>
  );
}

export default App;
