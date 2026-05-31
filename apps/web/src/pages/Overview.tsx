import { Card, Stat } from '../components/Card';
import { PageHeader } from '../components/PageHeader';
import { PageState } from '../components/PageState';
import {
  type CollectionRuns,
  type Overview,
  type OverviewVenueRow,
  useArtifact,
} from '../lib/api';
import {
  formatBps,
  formatCompact,
  formatPercent,
  formatUsd,
} from '../lib/format';

/** All critical Binance fields must be non-null for the data to be complete. */
function isOverviewComplete(data: Overview): boolean {
  const binance = data.venues?.binance;
  if (!binance) return true; // No binance section expected — accept as-is.
  return Object.values(binance).every(
    (row: OverviewVenueRow) =>
      row.index_price !== null &&
      row.futures_price !== null &&
      row.basis_rate !== null,
  );
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start || !end) return '—';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    completed:
      'bg-[color:var(--success)]/15 text-[color:var(--success)] border-[color:var(--success)]/30',
    failed:
      'bg-[color:var(--destructive)]/15 text-[color:var(--destructive)] border-[color:var(--destructive)]/30',
    running:
      'bg-[color:var(--warning)]/15 text-[color:var(--warning)] border-[color:var(--warning)]/30',
  };
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium ${colors[status] ?? 'bg-muted text-muted-foreground border-border'}`}
    >
      {status}
    </span>
  );
}

export default function OverviewPage() {
  const { data, error, loading } = useArtifact<Overview>('/api/overview', {
    validate: isOverviewComplete,
  });
  const { data: runsData } = useArtifact<CollectionRuns>('/api/runs');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        subtitle="Cross-venue snapshot: perp funding, futures basis, and open interest for BTC and ETH."
      />

      <PageState
        loading={loading}
        error={error}
        empty={!data || Object.keys(data.venues ?? {}).length === 0}
      >
        {data && (
          <div className="space-y-6">
            {data.venues.binance && (
              <div className="grid gap-5 lg:grid-cols-2">
                {Object.entries(data.venues.binance).map(([sym, row]) => (
                  <Card
                    key={sym}
                    title={`Binance USDT-M · ${sym}`}
                    subtitle="Latest funding, basis, open interest"
                  >
                    <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3">
                      <Stat
                        label="Index price"
                        value={formatUsd(row.index_price)}
                      />
                      <Stat
                        label="Futures price"
                        value={formatUsd(row.futures_price)}
                      />
                      <Stat
                        label="Basis"
                        value={formatBps(row.basis_rate)}
                        tone={
                          row.basis_rate === null
                            ? 'neutral'
                            : row.basis_rate > 0
                              ? 'positive'
                              : 'negative'
                        }
                      />
                      <Stat
                        label="Funding (8h)"
                        value={formatPercent(row.funding_rate_8h, 4)}
                      />
                      <Stat
                        label="Funding (annualized)"
                        value={formatPercent(row.annualized_funding, 1)}
                        tone={
                          row.annualized_funding === null
                            ? 'neutral'
                            : row.annualized_funding > 0
                              ? 'positive'
                              : 'negative'
                        }
                      />
                      <Stat
                        label="Open interest"
                        value={formatUsd(row.open_interest_usd, {
                          notation: 'compact',
                          maximumFractionDigits: 1,
                        })}
                      />
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {data.venues.deribit && (
              <Card
                title="Deribit · Futures &amp; perpetuals"
                subtitle="Mark price and open interest by expiry"
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="py-2 pr-4">Symbol</th>
                        <th className="py-2 pr-4">Kind</th>
                        <th className="py-2 pr-4">Expiry</th>
                        <th className="py-2 pr-4 text-right">Mark</th>
                        <th className="py-2 pr-4 text-right">Open interest</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono tabular-nums">
                      {Object.entries(data.venues.deribit)
                        .flatMap(([_, rows]) => rows)
                        .sort((a, b) =>
                          (a.expiry ?? 'z').localeCompare(b.expiry ?? 'z'),
                        )
                        .map((r) => (
                          <tr
                            key={r.symbol}
                            className="border-t border-border/60"
                          >
                            <td className="py-1.5 pr-4">{r.symbol}</td>
                            <td className="py-1.5 pr-4 text-muted-foreground">
                              {r.kind}
                            </td>
                            <td className="py-1.5 pr-4 text-muted-foreground">
                              {r.expiry?.slice(0, 10) ?? '—'}
                            </td>
                            <td className="py-1.5 pr-4 text-right">
                              {formatUsd(r.mark_price)}
                            </td>
                            <td className="py-1.5 pr-4 text-right">
                              {r.open_interest === null
                                ? '—'
                                : formatCompact(r.open_interest)}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {runsData && runsData.runs.length > 0 && (
              <Card
                title="Collection Health"
                subtitle="Recent data-collection runs"
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="py-2 pr-4">Started</th>
                        <th className="py-2 pr-4">Venue</th>
                        <th className="py-2 pr-4">Status</th>
                        <th className="py-2 pr-4 text-right">Duration</th>
                        <th className="py-2 pr-4 text-right">Records</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono tabular-nums">
                      {runsData.runs.slice(0, 10).map((run) => (
                        <tr
                          key={run.run_id}
                          className="border-t border-border/60"
                        >
                          <td className="py-1.5 pr-4 text-muted-foreground">
                            {run.started_at
                              ? new Date(run.started_at).toLocaleString()
                              : '—'}
                          </td>
                          <td className="py-1.5 pr-4">{run.venue}</td>
                          <td className="py-1.5 pr-4">
                            {statusBadge(run.status)}
                          </td>
                          <td className="py-1.5 pr-4 text-right">
                            {formatDuration(run.started_at, run.ended_at)}
                          </td>
                          <td className="py-1.5 pr-4 text-right">
                            {run.records_collected.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        )}
      </PageState>
    </div>
  );
}
