import { Info } from 'lucide-react';
import { Card, Stat } from '../components/Card';
import { PageState } from '../components/PageState';
import { useArtifact, type Signals } from '../lib/api';
import { formatPercent } from '../lib/format';

export default function SignalsPage() {
  const { data, error, loading } = useArtifact<Signals>('/api/signals');

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Signals</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Three headline regime signals: carry-vol divergence, skew stress,
          regime-change alert.
        </p>
      </header>

      <PageState
        loading={loading}
        error={error}
        empty={!data || data.summary.length === 0}
      >
        {data && (
          <>
            {data.as_of_snapshot && (
              <div className="flex items-start gap-3 rounded-lg border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 p-4 text-sm">
                <Info
                  size={16}
                  className="mt-0.5 shrink-0 text-[color:var(--warning)]"
                />
                <div>
                  <div className="font-semibold mb-0.5">
                    Snapshot mode — limited history
                  </div>
                  <p className="text-muted-foreground">{data.note}</p>
                </div>
              </div>
            )}

            <div className="grid gap-5 lg:grid-cols-2">
              {data.summary.map((row) => {
                const divergenceTone =
                  row.carry_vol_divergence === null
                    ? 'neutral'
                    : row.carry_vol_divergence > 0
                      ? 'positive'
                      : 'negative';
                return (
                  <Card
                    key={row.symbol}
                    title={`${row.symbol} · Carry-vol divergence`}
                    subtitle={`${row.currency} regime snapshot`}
                  >
                    <div className="grid grid-cols-2 gap-x-6 gap-y-5">
                      <Stat
                        label="Perp annualized funding"
                        value={formatPercent(row.perp_annualized_funding, 1)}
                      />
                      <Stat
                        label="Avg. dated carry"
                        value={formatPercent(row.average_dated_carry, 1)}
                      />
                      <Stat
                        label="Funding − dated carry"
                        value={formatPercent(row.carry_vol_divergence, 1)}
                        tone={divergenceTone}
                        hint="Positive = perp carry rich vs term curve"
                      />
                    </div>
                  </Card>
                );
              })}
            </div>

            <Card
              title="About the signal stack"
              subtitle="Definitions used in the analytics package"
            >
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <span className="text-foreground font-medium">
                    Carry-vol divergence:
                  </span>{' '}
                  rolling-percentile-rank(annualized carry) minus
                  rolling-percentile-rank(IV − RV). The snapshot view above is
                  a raw funding-vs-carry proxy until the rolling window is
                  populated.
                </li>
                <li>
                  <span className="text-foreground font-medium">
                    Skew stress:
                  </span>{' '}
                  average of front-end |25Δ risk-reversal| percentile and
                  open-interest concentration percentile.
                </li>
                <li>
                  <span className="text-foreground font-medium">
                    Regime-change alert:
                  </span>{' '}
                  fires when carry, skew, and OI percentiles all sit in their
                  top quintile (≥ 0.8) on the same day.
                </li>
              </ul>
            </Card>
          </>
        )}
      </PageState>
    </div>
  );
}
