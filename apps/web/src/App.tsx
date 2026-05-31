import { Route, Routes } from 'react-router-dom';
import { Header } from './components/Header';
import BenchmarksPage from './pages/Benchmarks';
import CarryPage from './pages/Carry';
import LearnPage from './pages/Learn';
import OverviewPage from './pages/Overview';
import SignalsPage from './pages/Signals';
import VolPage from './pages/Vol';

export default function App() {
  return (
    <div className="min-h-full">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/vol" element={<VolPage />} />
          <Route path="/carry" element={<CarryPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/benchmarks" element={<BenchmarksPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/learn/:slug" element={<LearnPage />} />
          <Route
            path="*"
            element={
              <div className="grid place-items-center py-24 text-sm text-muted-foreground">
                Not found.
              </div>
            }
          />
        </Routes>
      </main>
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        Basis &amp; Vol Lab · Deribit + Binance public market data
      </footer>
    </div>
  );
}
