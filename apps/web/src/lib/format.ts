export function formatPercent(
  x: number | null | undefined,
  digits = 2,
): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '—';
  return `${(x * 100).toFixed(digits)}%`;
}

/**
 * Narrow a Recharts tooltip value to a number.
 *
 * Recharts 3 widened its formatter parameter from `number` to
 * `ValueType | undefined`, i.e. `number | string | (number | string)[]`, because
 * a tooltip can be fed a stringified or stacked value. Every chart here plots a
 * single numeric series, so the extra cases are unreachable in practice -- but
 * they are reachable in the type, and asserting `as number` would push a real
 * `undefined` into `.toFixed()` and render "NaN%" rather than the em dash the
 * formatters below already produce for missing data.
 */
export function toNumber(x: unknown): number | null {
  if (typeof x === 'number') return x;
  // A single-element array is how a stacked series arrives.
  if (Array.isArray(x)) return x.length === 1 ? toNumber(x[0]) : null;
  if (typeof x === 'string' && x.trim() !== '') {
    const parsed = Number(x);
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
}

export function formatBps(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '—';
  return `${(x * 10_000).toFixed(1)} bps`;
}

const defaultUsdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

export function formatUsd(
  x: number | null | undefined,
  opts: Intl.NumberFormatOptions = {},
): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '—';
  if (Object.keys(opts).length === 0) return defaultUsdFormatter.format(x);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
    ...opts,
  }).format(x);
}

const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

export function formatCompact(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '—';
  return compactFormatter.format(x);
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return '—';
  const diff = (Date.now() - ts) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

/** Data older than 30 minutes is considered stale (GitHub cron is best-effort). */
const STALE_THRESHOLD_MS = 30 * 60 * 1000;

export function isStale(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return false;
  return Date.now() - ts > STALE_THRESHOLD_MS;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
