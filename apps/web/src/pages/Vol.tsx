import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '../components/Card';
import { PageState } from '../components/PageState';
import { useArtifact, type Vol } from '../lib/api';
import { formatPercent } from '../lib/format';
import { useTheme } from '../lib/theme';

function chartTokens(isDark: boolean) {
  return {
    grid: isDark ? 'oklch(0.28 0.02 250)' : 'oklch(0.92 0.005 240)',
    axis: isDark ? 'oklch(0.7 0.02 240)' : 'oklch(0.45 0.02 250)',
    line1: 'var(--color-chart-1)',
    line2: 'var(--color-chart-2)',
    bg: isDark ? 'oklch(0.2 0.015 250)' : 'white',
    fg: isDark ? 'oklch(0.96 0.005 240)' : 'oklch(0.18 0.02 250)',
  };
}

export default function VolPage() {
  const { data, error, loading } = useArtifact<Vol>('/api/vol');
  const { theme } = useTheme();
  const tokens = chartTokens(theme === 'dark');

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Volatility</h1>
        <p className="text-sm text-muted-foreground mt-1">
          ATM term structure and front-end smile, computed from Deribit option
          marks aligned to dated futures.
        </p>
      </header>

      <PageState
        loading={loading}
        error={error}
        empty={!data || Object.keys(data.by_currency).length === 0}
      >
        {data && (
          <div className="grid gap-6 lg:grid-cols-2">
            {Object.entries(data.by_currency).map(([ccy, payload]) => (
              <div key={ccy} className="space-y-6">
                <Card
                  title={`${ccy} · ATM term structure`}
                  subtitle={`${payload.atm_term_structure.length} expiries`}
                >
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={payload.atm_term_structure.map((p) => ({
                          tte: Number(p.tte_years.toFixed(4)),
                          iv: p.mark_iv,
                          expiry: p.expiry.slice(0, 10),
                        }))}
                        margin={{ top: 8, right: 16, bottom: 6, left: 0 }}
                      >
                        <CartesianGrid
                          stroke={tokens.grid}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="tte"
                          stroke={tokens.axis}
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v: number) =>
                            v < 1 / 12
                              ? `${Math.round(v * 365)}d`
                              : `${(v * 12).toFixed(1)}m`
                          }
                          label={{
                            value: 'time to expiry',
                            position: 'insideBottom',
                            offset: -2,
                            fill: tokens.axis,
                            fontSize: 11,
                          }}
                        />
                        <YAxis
                          stroke={tokens.axis}
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                          width={48}
                        />
                        <Tooltip
                          contentStyle={{
                            background: tokens.bg,
                            border: `1px solid ${tokens.grid}`,
                            color: tokens.fg,
                            fontSize: 12,
                          }}
                          formatter={(value: number) =>
                            formatPercent(value, 2)
                          }
                          labelFormatter={(_v, payload) =>
                            payload?.[0]?.payload?.expiry ?? ''
                          }
                        />
                        <Line
                          dataKey="iv"
                          name="ATM IV"
                          stroke={tokens.line1}
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                <Card
                  title={`${ccy} · Front-end smile`}
                  subtitle={`expiry ${payload.smile.expiry.slice(0, 10)} · ${
                    payload.smile.points.length
                  } strikes`}
                >
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={payload.smile.points.map((p) => ({
                          moneyness: Number(p.moneyness.toFixed(4)),
                          iv: p.mark_iv,
                          strike: p.strike,
                        }))}
                        margin={{ top: 8, right: 16, bottom: 6, left: 0 }}
                      >
                        <CartesianGrid
                          stroke={tokens.grid}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="moneyness"
                          stroke={tokens.axis}
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v: number) => v.toFixed(2)}
                          label={{
                            value: 'K / F',
                            position: 'insideBottom',
                            offset: -2,
                            fill: tokens.axis,
                            fontSize: 11,
                          }}
                        />
                        <YAxis
                          stroke={tokens.axis}
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                          width={48}
                        />
                        <Tooltip
                          contentStyle={{
                            background: tokens.bg,
                            border: `1px solid ${tokens.grid}`,
                            color: tokens.fg,
                            fontSize: 12,
                          }}
                          formatter={(value: number) =>
                            formatPercent(value, 2)
                          }
                          labelFormatter={(_v, payload) =>
                            `K = ${payload?.[0]?.payload?.strike ?? ''}`
                          }
                        />
                        <Line
                          dataKey="iv"
                          name="Mark IV"
                          stroke={tokens.line2}
                          strokeWidth={2}
                          dot={{ r: 2 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            ))}
          </div>
        )}
      </PageState>
    </div>
  );
}
