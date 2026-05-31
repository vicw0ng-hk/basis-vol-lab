import { useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, Stat } from '../components/Card';
import { InfoIcon } from '../components/Icons';
import { PageHeader } from '../components/PageHeader';
import { PageState } from '../components/PageState';
import {
  type HistoryDates,
  type HistorySnapshot,
  useArtifact,
} from '../lib/api';
import { chartTokens } from '../lib/chart';
import { formatCompact, formatPercent } from '../lib/format';
import { useTheme } from '../lib/theme';

function DiffBadge({
  value,
  format = 'number',
}: {
  value: number | null;
  format?: 'number' | 'percent' | 'iv';
}) {
  if (value === null || value === undefined) return <span>—</span>;
  const isPositive = value > 0;
  const sign = isPositive ? '+' : '';
  const color = isPositive
    ? 'text-[color:var(--positive)]'
    : value < 0
      ? 'text-[color:var(--negative)]'
      : 'text-muted-foreground';

  let formatted: string;
  if (format === 'percent') {
    formatted = `${sign}${(value * 100).toFixed(1)}%`;
  } else if (format === 'iv') {
    formatted = `${sign}${(value * 100).toFixed(2)}pp`;
  } else {
    formatted = `${sign}${value}`;
  }

  return <span className={`font-mono text-sm ${color}`}>{formatted}</span>;
}

export default function HistoryPage() {
  const {
    data: datesData,
    loading: datesLoading,
    error: datesError,
  } = useArtifact<HistoryDates>('/api/history/dates');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const { theme } = useTheme();
  const tokens = chartTokens(theme === 'dark');

  const activeDate = selectedDate ?? datesData?.dates.at(-1) ?? null;

  const {
    data: snapshot,
    loading: snapLoading,
    error: snapError,
  } = useArtifact<HistorySnapshot>(
    activeDate ? `/api/history/${activeDate}` : '/api/history/dates',
    [activeDate],
  );

  const dates = datesData?.dates ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Historical Replay"
        subtitle="Browse Deribit option and futures snapshots stored in Parquet, with day-over-day change summaries."
      />

      <PageState
        loading={datesLoading}
        error={datesError}
        empty={dates.length === 0}
      >
        <div className="flex flex-wrap items-center gap-3">
          <label
            htmlFor="date-select"
            className="text-sm font-medium text-muted-foreground"
          >
            Snapshot date
          </label>
          <select
            id="date-select"
            value={activeDate ?? ''}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {dates.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <span className="text-xs text-muted-foreground">
            {dates.length} snapshot{dates.length !== 1 ? 's' : ''} available
          </span>
        </div>

        {activeDate && (
          <PageState loading={snapLoading} error={snapError} empty={!snapshot}>
            {snapshot && (
              <div className="space-y-6">
                {/* Summary stats */}
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                  <Card title="Options" subtitle="Deribit option tickers">
                    <Stat
                      label="Count"
                      value={snapshot.option_count.toLocaleString()}
                    />
                  </Card>
                  <Card title="Futures" subtitle="Futures & perpetuals">
                    <Stat
                      label="Count"
                      value={snapshot.future_count.toLocaleString()}
                    />
                  </Card>
                  <Card
                    title="Open Interest"
                    subtitle="Total Deribit futures OI"
                  >
                    <Stat
                      label="Contracts"
                      value={formatCompact(snapshot.total_open_interest)}
                    />
                  </Card>
                  <Card title="Snapshot Time" subtitle="UTC timestamp">
                    <Stat
                      label="Captured"
                      value={
                        snapshot.timestamp
                          ? new Date(snapshot.timestamp).toLocaleString()
                          : '—'
                      }
                    />
                  </Card>
                </div>

                {/* ATM IV per currency */}
                <Card
                  title="Average ATM IV"
                  subtitle="Mean across expiries by currency"
                >
                  <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
                    {Object.entries(snapshot.avg_atm_iv).map(([ccy, iv]) => (
                      <Stat
                        key={ccy}
                        label={ccy}
                        value={formatPercent(iv, 1)}
                      />
                    ))}
                  </div>
                </Card>

                {/* ATM term structure charts */}
                {Object.entries(snapshot.atm_term_structure).map(
                  ([ccy, points]) => (
                    <Card
                      key={ccy}
                      title={`${ccy} · ATM Term Structure`}
                      subtitle={`${points.length} expiries on ${snapshot.date}`}
                    >
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={points.map((p) => ({
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
                              tickFormatter={(v: number) =>
                                `${(v * 100).toFixed(0)}%`
                              }
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
                  ),
                )}

                {/* Futures table */}
                {Object.entries(snapshot.futures).map(([ccy, futs]) => (
                  <Card
                    key={ccy}
                    title={`${ccy} · Futures & Perpetuals`}
                    subtitle="Mark price and open interest"
                  >
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                          <tr>
                            <th className="py-2 pr-4">Symbol</th>
                            <th className="py-2 pr-4">Kind</th>
                            <th className="py-2 pr-4">Expiry</th>
                            <th className="py-2 pr-4 text-right">Mark price</th>
                            <th className="py-2 text-right">Open interest</th>
                          </tr>
                        </thead>
                        <tbody className="font-mono tabular-nums">
                          {futs
                            .sort((a, b) =>
                              (a.expiry ?? 'z').localeCompare(b.expiry ?? 'z'),
                            )
                            .map((f) => (
                              <tr
                                key={f.symbol}
                                className="border-t border-border/60"
                              >
                                <td className="py-1.5 pr-4">{f.symbol}</td>
                                <td className="py-1.5 pr-4 text-muted-foreground">
                                  {f.kind}
                                </td>
                                <td className="py-1.5 pr-4 text-muted-foreground">
                                  {f.expiry?.slice(0, 10) ?? '—'}
                                </td>
                                <td className="py-1.5 pr-4 text-right">
                                  $
                                  {f.mark_price.toLocaleString(undefined, {
                                    maximumFractionDigits: 2,
                                  })}
                                </td>
                                <td className="py-1.5 text-right">
                                  {f.open_interest != null
                                    ? formatCompact(f.open_interest)
                                    : '—'}
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                ))}

                {/* Day-over-day diff */}
                {snapshot.diff ? (
                  <Card
                    title="What Changed?"
                    subtitle={`Compared to previous snapshot (${snapshot.diff.previous_date})`}
                  >
                    <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                          Options Δ
                        </span>
                        <DiffBadge value={snapshot.diff.option_count_delta} />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                          Futures Δ
                        </span>
                        <DiffBadge value={snapshot.diff.future_count_delta} />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                          OI Change
                        </span>
                        <DiffBadge
                          value={snapshot.diff.oi_change}
                          format="percent"
                        />
                      </div>
                    </div>

                    {Object.keys(snapshot.diff.atm_iv_changes).length > 0 && (
                      <div className="mt-4 border-t border-border pt-4">
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                          ATM IV Changes
                        </h4>
                        <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
                          {Object.entries(snapshot.diff.atm_iv_changes).map(
                            ([ccy, change]) => (
                              <div key={ccy} className="flex flex-col gap-0.5">
                                <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                                  {ccy}
                                </span>
                                <DiffBadge value={change.delta} format="iv" />
                                <span className="text-[10px] text-muted-foreground">
                                  {formatPercent(change.previous, 1)} →{' '}
                                  {formatPercent(change.current, 1)}
                                </span>
                              </div>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                  </Card>
                ) : (
                  <div className="flex items-start gap-3 rounded-lg border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 p-4 text-sm">
                    <InfoIcon />
                    <div>
                      <div className="font-semibold mb-0.5">
                        No previous snapshot
                      </div>
                      <p className="text-muted-foreground">
                        This is the earliest available date — there is no prior
                        snapshot to compare against.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </PageState>
        )}
      </PageState>
    </div>
  );
}
