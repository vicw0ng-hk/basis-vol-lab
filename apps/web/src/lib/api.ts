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
  observations?: number;
  window?: string;
  note?: string;
  summary: Array<{
    symbol: string;
    currency: string;
    perp_annualized_funding: number | null;
    average_dated_carry: number | null;
    atm_iv: number | null;
    open_interest: number | null;
    carry_vol_divergence: number | null;
    funding_pctile: number | null;
    carry_pctile: number | null;
    iv_pctile: number | null;
    oi_pctile: number | null;
  }>;
};

export type CollectionRunRow = {
  run_id: string;
  venue: string;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  records_collected: number;
};

export type CollectionRuns = {
  runs: CollectionRunRow[];
  note?: string;
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

export type GetJsonOptions<T> = {
  signal?: AbortSignal;
  /** Return true if data is complete; false triggers a retry with backoff. */
  validate?: (data: T) => boolean;
};

async function getJson<T>(
  path: string,
  options?: AbortSignal | GetJsonOptions<T>,
): Promise<T> {
  // Support legacy call-sites passing just a signal.
  const opts: GetJsonOptions<T> =
    options instanceof AbortSignal ? { signal: options } : (options ?? {});
  const { signal, validate } = opts;

  const url = API_BASE ? `${API_BASE}${path}` : path;
  const INITIAL_DELAY_MS = 800;
  const MAX_DELAY_MS = 4000;
  // Trigger a bootstrap refresh after this many consecutive 503s.
  const BOOTSTRAP_AFTER = 2;
  // Re-trigger bootstrap every N additional 503s if the first attempt failed.
  const BOOTSTRAP_RETRY_EVERY = 5;
  // Max retries for incomplete (validation-failed) responses before accepting.
  const MAX_INCOMPLETE_RETRIES = 10;

  let attempt = 0;
  let consecutive503 = 0;
  let incompleteRetries = 0;

  // Retry indefinitely on 502/503/504 until data is available.
  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

    const res = await fetch(url, { signal });
    if (res.ok) {
      const data = (await res.json()) as T;
      // If a validator is provided and the data is incomplete, retry with
      // backoff up to a limit — then accept whatever we have.
      if (validate && !validate(data)) {
        incompleteRetries++;
        if (incompleteRetries >= MAX_INCOMPLETE_RETRIES) return data;
        // Trigger a refresh to regenerate data on the backend.
        if (incompleteRetries === 1) await bootstrapRefresh();
        const delay = Math.min(
          INITIAL_DELAY_MS * incompleteRetries,
          MAX_DELAY_MS,
        );
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      return data;
    }

    if (res.status >= 502 && res.status <= 504) {
      attempt++;
      if (res.status === 503) consecutive503++;

      // After a couple of 503s (artifact not found), auto-trigger a refresh
      // to generate the data rather than just retrying the GET forever.
      if (consecutive503 === BOOTSTRAP_AFTER) {
        await bootstrapRefresh();
      } else if (
        consecutive503 > BOOTSTRAP_AFTER &&
        (consecutive503 - BOOTSTRAP_AFTER) % BOOTSTRAP_RETRY_EVERY === 0
      ) {
        // Previous bootstrap may have failed (Lambda timeout, network error).
        // Fire-and-forget a retry without blocking the GET loop.
        void bootstrapRefresh();
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

export type UseArtifactOptions<T> = {
  deps?: unknown[];
  /** Return true if data is complete; false triggers a retry with backoff. */
  validate?: (data: T) => boolean;
};

export function useArtifact<T>(
  path: string,
  options?: unknown[] | UseArtifactOptions<T>,
): FetchState<T> {
  // Support legacy call-sites passing just deps array.
  const opts: UseArtifactOptions<T> = Array.isArray(options)
    ? { deps: options }
    : (options ?? {});
  const { deps = [], validate } = opts;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  // Generation counter incremented *synchronously* on refresh so in-flight
  // promise callbacks from a previous fetch cycle see the new value before
  // React re-renders and runs effect cleanup.  This prevents a brief flash
  // of stale data when a refresh races with a completing fetch.
  const fetchGenRef = useRef(0);

  const refresh = useCallback(() => {
    fetchGenRef.current++;
    setTick((t) => t + 1);
  }, []);

  // Stable ref for validate to avoid re-triggering effects.
  const validateRef = useRef(validate);
  validateRef.current = validate;

  // Listen for global refresh events (triggered by the header refresh button).
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    const handler = () => refreshRef.current();
    window.addEventListener(REFRESH_EVENT, handler);
    return () => window.removeEventListener(REFRESH_EVENT, handler);
  }, []);

  useEffect(() => {
    const gen = fetchGenRef.current;
    const controller = new AbortController();
    setLoading(true);
    getJson<T>(path, {
      signal: controller.signal,
      validate: validateRef.current,
    })
      .then((d) => {
        if (fetchGenRef.current === gen && !controller.signal.aborted) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (fetchGenRef.current === gen && !controller.signal.aborted) {
          if (e instanceof DOMException && e.name === 'AbortError') return;
          setError(e instanceof Error ? e.message : String(e));
        }
      })
      .finally(() => {
        if (fetchGenRef.current === gen && !controller.signal.aborted)
          setLoading(false);
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
