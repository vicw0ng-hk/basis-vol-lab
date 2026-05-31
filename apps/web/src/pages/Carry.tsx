import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, Stat } from '../components/Card';
import { PageHeader } from '../components/PageHeader';
import { PageState } from '../components/PageState';
import { type Carry, useArtifact } from '../lib/api';
import { chartTokens } from '../lib/chart';
import { formatPercent, formatUsd } from '../lib/format';
import { useTheme } from '../lib/theme';

/** Carry data is incomplete if the cards object is empty. */
function isCarryComplete(data: Carry): boolean {
  return Object.keys(data.cards).length > 0;
}

export default function CarryPage() {
  const { data, error, loading } = useArtifact<Carry>('/api/carry', {
    validate: isCarryComplete,
  });
  const { theme } = useTheme();
  const { grid, axis, bg, fg } = chartTokens(theme === 'dark');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Carry"
        subtitle="Annualized perp funding versus dated-futures basis. Funding history is the trailing 100-row window from Binance."
      />

      <PageState
        loading={loading}
        error={error}
        empty={!data || Object.keys(data.cards).length === 0}
      >
        {data && (
          <div className="grid gap-6 lg:grid-cols-2">
            {Object.entries(data.cards).map(([sym, card]) => {
              const fundingTone =
                card.perp_annualized_funding === null
                  ? 'neutral'
                  : card.perp_annualized_funding >= 0
                    ? 'positive'
                    : 'negative';
              return (
                <Card
                  key={sym}
                  title={`${sym} · Carry`}
                  subtitle={`${card.currency} index ${formatUsd(card.index_price)}`}
                >
                  <div className="grid grid-cols-2 gap-x-6 gap-y-5">
                    <Stat
                      label="Perp annualized funding"
                      value={formatPercent(card.perp_annualized_funding, 1)}
                      tone={fundingTone}
                    />
                    <Stat
                      label="Dated futures (count)"
                      value={String(card.dated_carry.length)}
                    />
                  </div>

                  {card.perp_funding_history.length > 0 && (
                    <div className="mt-6 h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={card.perp_funding_history.map((h) => ({
                            ts: h.ts.slice(5, 16).replace('T', ' '),
                            funding: h.annualized_funding,
                          }))}
                          margin={{ top: 6, right: 16, bottom: 0, left: 0 }}
                        >
                          <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                          <XAxis
                            dataKey="ts"
                            stroke={axis}
                            tick={{ fontSize: 10 }}
                            interval="preserveStartEnd"
                            minTickGap={32}
                          />
                          <YAxis
                            stroke={axis}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(v: number) =>
                              `${(v * 100).toFixed(0)}%`
                            }
                            width={40}
                          />
                          <Tooltip
                            contentStyle={{
                              background: bg,
                              border: `1px solid ${grid}`,
                              color: fg,
                              fontSize: 12,
                            }}
                            formatter={(value: number) =>
                              formatPercent(value, 2)
                            }
                          />
                          <defs>
                            <linearGradient
                              id={`grad-${sym}`}
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="0%"
                                stopColor="var(--color-chart-1)"
                                stopOpacity={0.45}
                              />
                              <stop
                                offset="100%"
                                stopColor="var(--color-chart-1)"
                                stopOpacity={0.02}
                              />
                            </linearGradient>
                          </defs>
                          <Area
                            type="monotone"
                            dataKey="funding"
                            stroke="var(--color-chart-1)"
                            strokeWidth={2}
                            fill={`url(#grad-${sym})`}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {card.dated_carry.length > 0 && (
                    <div className="mt-6 overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                          <tr>
                            <th className="py-1.5 pr-4">Expiry</th>
                            <th className="py-1.5 pr-4 text-right">Days</th>
                            <th className="py-1.5 pr-4 text-right">Future</th>
                            <th className="py-1.5 text-right">Ann. carry</th>
                          </tr>
                        </thead>
                        <tbody className="font-mono tabular-nums">
                          {card.dated_carry.map((d) => (
                            <tr
                              key={d.expiry}
                              className="border-t border-border/60"
                            >
                              <td className="py-1.5 pr-4">
                                {d.expiry.slice(0, 10)}
                              </td>
                              <td className="py-1.5 pr-4 text-right">
                                {d.days_to_expiry.toFixed(0)}
                              </td>
                              <td className="py-1.5 pr-4 text-right">
                                {formatUsd(d.future_price)}
                              </td>
                              <td
                                className={
                                  'py-1.5 text-right ' +
                                  (d.annualized_carry >= 0
                                    ? 'text-[color:var(--positive)]'
                                    : 'text-[color:var(--negative)]')
                                }
                              >
                                {formatPercent(d.annualized_carry, 1)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </PageState>
    </div>
  );
}
