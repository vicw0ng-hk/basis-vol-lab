import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, Stat } from '../components/Card';
import { PageHeader } from '../components/PageHeader';
import benchmarkData from '../data/benchmarks.json';
import { chartTokens } from '../lib/chart';
import { useTheme } from '../lib/theme';

type BenchmarkResult = {
  name: string;
  label: string;
  category: string;
  param: string | null;
  mean_ms: number;
  median_ms: number;
  stddev_ms: number;
  ops: number;
  rounds: number;
};

type BenchmarkData = {
  hardware: {
    cpu: string;
    arch: string;
    cores: number;
    python: string;
    system: string;
  };
  results: BenchmarkResult[];
};

const data = benchmarkData as BenchmarkData;

const CATEGORIES: { key: string; title: string; subtitle: string }[] = [
  {
    key: 'iv',
    title: 'IV Inversion',
    subtitle:
      "Implied volatility solve via Brent's method — scalar loop vs. vectorized vs. parallel",
  },
  {
    key: 'greeks',
    title: 'Greeks & Pricing',
    subtitle:
      'Black-76 pricing, Greeks, and PCHIP smile interpolation throughput',
  },
  {
    key: 'snapshot',
    title: 'Snapshot Pipeline',
    subtitle:
      'Compute-only stages: term structure, RV estimators, basis curve, JSON serialization',
  },
];

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  if (ms >= 1) return `${ms.toFixed(2)}ms`;
  return `${(ms * 1000).toFixed(1)}μs`;
}

function BenchmarkTable({ results }: { results: BenchmarkResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="py-2 pr-4">Benchmark</th>
            <th className="py-2 pr-4 text-right">Mean</th>
            <th className="py-2 pr-4 text-right">Median</th>
            <th className="py-2 pr-4 text-right">Std dev</th>
            <th className="py-2 text-right">Ops/s</th>
          </tr>
        </thead>
        <tbody className="font-mono tabular-nums">
          {results.map((r) => (
            <tr key={r.name} className="border-t border-border/60">
              <td className="py-1.5 pr-4 font-sans">{r.label}</td>
              <td className="py-1.5 pr-4 text-right">{formatMs(r.mean_ms)}</td>
              <td className="py-1.5 pr-4 text-right">
                {formatMs(r.median_ms)}
              </td>
              <td className="py-1.5 pr-4 text-right">
                ±{formatMs(r.stddev_ms)}
              </td>
              <td className="py-1.5 text-right">
                {r.ops >= 1000
                  ? `${(r.ops / 1000).toFixed(1)}k`
                  : r.ops.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ThroughputChart({ results }: { results: BenchmarkResult[] }) {
  const { theme } = useTheme();
  const tokens = chartTokens(theme === 'dark');

  // Only chart results that have meaningful ops (> 1)
  const chartData = results
    .filter((r) => r.ops >= 1)
    .map((r) => ({
      label: r.label.length > 35 ? `${r.label.slice(0, 32)}…` : r.label,
      ops: r.ops,
    }));

  if (chartData.length === 0) return null;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
        >
          <CartesianGrid
            stroke={tokens.grid}
            strokeDasharray="3 3"
            horizontal={false}
          />
          <XAxis
            type="number"
            stroke={tokens.axis}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
            }
          />
          <YAxis
            type="category"
            dataKey="label"
            stroke={tokens.axis}
            tick={{ fontSize: 10 }}
            width={200}
          />
          <Tooltip
            contentStyle={{
              background: tokens.bg,
              border: `1px solid ${tokens.grid}`,
              color: tokens.fg,
              fontSize: 12,
            }}
            formatter={(value: number) => [
              `${value.toFixed(1)} ops/s`,
              'Throughput',
            ]}
          />
          <Bar
            dataKey="ops"
            fill={tokens.line1}
            radius={[0, 4, 4, 0]}
            barSize={20}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function BenchmarksPage() {
  const { hardware, results } = data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Benchmarks"
        subtitle="Performance profiles for the analytics engine, measured with pytest-benchmark."
      />

      <Card
        title="Hardware Context"
        subtitle="Environment used for this benchmark run"
      >
        <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-5">
          <Stat label="CPU" value={hardware.cpu} />
          <Stat label="Architecture" value={hardware.arch} />
          <Stat label="Cores" value={String(hardware.cores)} />
          <Stat label="Python" value={hardware.python} />
          <Stat label="System" value={hardware.system} />
        </div>
      </Card>

      {CATEGORIES.map(({ key, title, subtitle }) => {
        const catResults = results.filter((r) => r.category === key);
        if (catResults.length === 0) return null;
        return (
          <Card key={key} title={title} subtitle={subtitle}>
            <BenchmarkTable results={catResults} />
            <div className="mt-6 border-t border-border/60 pt-4">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
                Throughput (ops/s)
              </div>
              <ThroughputChart results={catResults} />
            </div>
          </Card>
        );
      })}

      <Card
        title="About these benchmarks"
        subtitle="How to reproduce and interpret results"
      >
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>
            All benchmarks use{' '}
            <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
              pytest-benchmark
            </code>{' '}
            with synthetic data at realistic scales. Network I/O is excluded to
            isolate compute performance.
          </p>
          <p>
            <span className="text-foreground font-medium">Reproduce:</span>{' '}
            <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
              mise run bench
            </code>{' '}
            or{' '}
            <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
              uv run python scripts/export_benchmarks.py
            </code>{' '}
            to regenerate this page's data.
          </p>
          <p>
            <span className="text-foreground font-medium">IV inversion</span> is
            the most expensive operation. The vectorized wrapper (
            <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
              implied_vol_array
            </code>
            ) matches the scalar loop because each solve requires independent
            Brent iterations. The parallel variant adds process-pool overhead at
            small sizes but can speed up 10k+ chains on multi-core hardware.
          </p>
          <p>
            <span className="text-foreground font-medium">
              Greeks & pricing
            </span>{' '}
            are fully vectorized NumPy and run orders of magnitude faster than
            scalar loops — processing 10k options in under 1 ms.
          </p>
        </div>
      </Card>
    </div>
  );
}
