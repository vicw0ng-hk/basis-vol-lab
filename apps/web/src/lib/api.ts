import { useCallback, useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export type Meta = {
  generated_at: string;
  deribit_options: number;
  deribit_futures: number;
  binance_symbols: string[];
  binance_funding_rows: number;
};

export type OverviewVenueRow = {
  funding_rate_8h: number | null;
  annualized_funding: number | null;
  basis_rate: number | null;
  futures_price: number | null;
  index_price: number | null;
  open_interest_usd: number | null;
};

export type Overview = {
  venues: {
    binance?: Record<string, OverviewVenueRow>;
    deribit?: Record<
      string,
      Array<{
        symbol: string;
        kind: string;
        expiry: string | null;
        mark_price: number;
        open_interest: number | null;
        funding_rate_8h: number | null;
      }>
    >;
  };
};

export type AtmTermPoint = {
  expiry: string;
  strike: number;
  forward: number;
  mark_iv: number;
  tte_years: number;
};

export type SmilePoint = {
  strike: number;
  moneyness: number;
  mark_iv: number;
};

export type Vol = {
  by_currency: Record<
    string,
    {
      atm_term_structure: AtmTermPoint[];
      smile: { expiry: string; points: SmilePoint[] };
    }
  >;
};

export type Carry = {
  cards: Record<
    string,
    {
      currency: string;
      index_price: number;
      perp_annualized_funding: number | null;
      perp_funding_history: Array<{ ts: string; annualized_funding: number }>;
      dated_carry: Array<{
        expiry: string;
        days_to_expiry: number;
        future_price: number;
        annualized_carry: number;
      }>;
    }
  >;
};

export type Signals = {
  as_of_snapshot: boolean;
  note: string;
  summary: Array<{
    symbol: string;
    currency: string;
    perp_annualized_funding: number | null;
    average_dated_carry: number | null;
    carry_vol_divergence: number | null;
  }>;
};

async function getJson<T>(path: string): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  const maxRetries = 4;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await fetch(url);
    if (res.ok) return res.json() as Promise<T>;
    // Retry on 502/503/504 (cold-start / transient errors)
    if (attempt < maxRetries && res.status >= 502 && res.status <= 504) {
      await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
      continue;
    }
    let detail: string | undefined;
    try {
      detail = (await res.json())?.detail;
    } catch {
      // ignore
    }
    throw new Error(detail ?? `HTTP ${res.status} from ${path}`);
  }
  throw new Error(`Failed to fetch ${path} after ${maxRetries + 1} attempts`);
}

export type FetchState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
};

export function useArtifact<T>(path: string, deps: unknown[] = []): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getJson<T>(path)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  return { data, error, loading, refresh };
}

export async function triggerRefresh(): Promise<Meta> {
  const url = API_BASE ? `${API_BASE}/api/refresh` : '/api/refresh';
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`refresh failed: HTTP ${res.status}`);
  return res.json() as Promise<Meta>;
}
