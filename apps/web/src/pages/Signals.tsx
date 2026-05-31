import { Card, Stat } from '../components/Card';
import { InfoIcon } from '../components/Icons';
import { PageHeader } from '../components/PageHeader';
import { PageState } from '../components/PageState';
import { type Signals, useArtifact } from '../lib/api';
import { formatPercent } from '../lib/format';

/** Signals data is incomplete if the summary array is empty. */
function isSignalsComplete(data: Signals): boolean {
  return data.summary.length > 0;
}

function formatPctile(v: number | null | undefined): string {
  if (v == null) return '—';
  return `${(v * 100).toFixed(0)}th`;
}

export default function SignalsPage() {
  const { data, error, loading } = useArtifact<Signals>('/api/signals', {
    validate: isSignalsComplete,
  });

  const hasRolling = data != null && !data.as_of_snapshot;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Signals"
        subtitle="Three headline regime signals: carry-vol divergence, skew stress, regime-change alert."
      />

      <PageState
        loading={loading}
        error={error}
        empty={!data || data.summary.length === 0}
      >
        {data && (
          <>
            {data.as_of_snapshot && (
              <div className="flex items-start gap-3 rounded-lg border border-[color:var(--warning)]/40 bg-[color:var(--warning)]/10 p-4 text-sm">
                <InfoIcon />
                <div>
                  <div className="font-semibold mb-0.5">
                    Snapshot mode — limited history
                  </div>
                  <p className="text-muted-foreground">
                    {data.note ??
                      'Rolling-percentile signals appear once the historical snapshot store has enough observations.'}
                  </p>
                </div>
              </div>
            )}

            {hasRolling && (
              <div className="flex items-start gap-3 rounded-lg border border-[color:var(--success)]/40 bg-[color:var(--success)]/10 p-4 text-sm">
                <InfoIcon />
                <div>
                  <div className="font-semibold mb-0.5">
                    Rolling percentiles active
                  </div>
                  <p className="text-muted-foreground">
                    Based on {data.observations ?? 0} observations over a{' '}
                    {data.window ?? '365D'} window.
                  </p>
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
                    subtitle={`${row.currency} regime ${hasRolling ? 'percentile' : 'snapshot'}`}
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
                      {hasRolling && (
                        <Stat
                          label="ATM IV"
                          value={formatPercent(row.atm_iv, 1)}
                        />
                      )}
                    </div>

                    {hasRolling && (
                      <div className="mt-4 border-t border-border pt-4">
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                          Percentile Ranks
                        </h4>
                        <div className="grid grid-cols-4 gap-3">
                          <Stat
                            label="Funding"
                            value={formatPctile(row.funding_pctile)}
                          />
                          <Stat
                            label="Carry"
                            value={formatPctile(row.carry_pctile)}
                          />
                          <Stat
                            label="IV"
                            value={formatPctile(row.iv_pctile)}
                          />
                          <Stat
                            label="OI"
                            value={formatPctile(row.oi_pctile)}
                          />
                        </div>
                      </div>
                    )}
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
                  rolling-percentile-rank(IV − RV).{' '}
                  {data.as_of_snapshot
                    ? 'The snapshot view above is a raw funding-vs-carry proxy until the rolling window is populated.'
                    : `Currently computed over ${data.observations ?? 0} observations.`}
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
