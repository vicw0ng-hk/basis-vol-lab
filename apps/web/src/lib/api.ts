import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

// Global refresh signal: all useArtifact hooks re-fetch when this fires.
const REFRESH_EVENT = 'basis:refresh';

function emitGlobalRefresh() {
  window.dispatchEvent(new Event(REFRESH_EVENT));
}

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

// Track whether a bootstrap refresh is already in-flight so multiple hooks
// don't trigger concurrent refreshes.
let _bootstrapInFlight: Promise<void> | null = null;

async function bootstrapRefresh(): Promise<void> {
  if (_bootstrapInFlight) return _bootstrapInFlight;
  _bootstrapInFlight = (async () => {
    const url = API_BASE ? `${API_BASE}/api/refresh` : '/api/refresh';
    try {
      await fetch(url, { method: 'POST' });
    } catch {
      // ignore – the subsequent GET retry will detect success or keep looping
    } finally {
      _bootstrapInFlight = null;
    }
  })();
  return _bootstrapInFlight;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  const INITIAL_DELAY_MS = 800;
  const MAX_DELAY_MS = 4000;
  // Trigger a bootstrap refresh after this many consecutive 503s.
  const BOOTSTRAP_AFTER = 2;

  let attempt = 0;
  let consecutive503 = 0;

  // Retry indefinitely on 502/503/504 until data is available.
  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

    const res = await fetch(url, { signal });
    if (res.ok) return res.json() as Promise<T>;

    if (res.status >= 502 && res.status <= 504) {
      attempt++;
      if (res.status === 503) consecutive503++;

      // After a couple of 503s (artifact not found), auto-trigger a refresh
      // to generate the data rather than just retrying the GET forever.
      if (consecutive503 === BOOTSTRAP_AFTER) {
        await bootstrapRefresh();
      }

      const delay = Math.min(INITIAL_DELAY_MS * attempt, MAX_DELAY_MS);
      await new Promise((r) => setTimeout(r, delay));
      continue;
    }

    // Non-retryable error
    let detail: string | undefined;
    try {
      detail = (await res.json())?.detail;
    } catch {
      // ignore
    }
    throw new Error(detail ?? `HTTP ${res.status} from ${path}`);
  }
}

export type FetchState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
};

export function useArtifact<T>(
  path: string,
  deps: unknown[] = [],
): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  // Listen for global refresh events (triggered by the header refresh button).
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    const handler = () => refreshRef.current();
    window.addEventListener(REFRESH_EVENT, handler);
    return () => window.removeEventListener(REFRESH_EVENT, handler);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getJson<T>(path, controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!controller.signal.aborted) {
          if (e instanceof DOMException && e.name === 'AbortError') return;
          setError(e instanceof Error ? e.message : String(e));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  return { data, error, loading, refresh };
}

export async function triggerRefresh(): Promise<Meta> {
  const url = API_BASE ? `${API_BASE}/api/refresh` : '/api/refresh';
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`refresh failed: HTTP ${res.status}`);
  const meta = (await res.json()) as Meta;
  // Signal all useArtifact hooks to re-fetch.
  emitGlobalRefresh();
  return meta;
}
