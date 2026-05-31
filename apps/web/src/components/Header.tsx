import { useEffect, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { type Meta, triggerRefresh, useArtifact } from '../lib/api';
import { formatRelative, isStale } from '../lib/format';
import { ActivityIcon, MenuIcon, RefreshIcon, XIcon } from './Icons';
import { ThemeToggle } from './ThemeToggle';

const AUTO_REFRESH_MS = 5 * 60 * 1000; // 5 minutes
const TICK_MS = 10_000; // update relative timestamp every 10s
const LS_AUTO_REFRESH = 'basis:auto-refresh';

const NAV = [
  { to: '/', label: 'Overview', end: true },
  { to: '/vol', label: 'Volatility' },
  { to: '/carry', label: 'Carry' },
  { to: '/signals', label: 'Signals' },
  { to: '/benchmarks', label: 'Benchmarks' },
  { to: '/learn', label: 'Learn' },
];

export function Header() {
  const meta = useArtifact<Meta>('/api/meta');
  const [refreshing, setRefreshing] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [, setNow] = useState(Date.now()); // tick to update relative time
  const [autoRefresh, setAutoRefresh] = useState(() => {
    const stored = localStorage.getItem(LS_AUTO_REFRESH);
    return stored === null ? true : stored === '1';
  });
  const autoRefreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoRefreshRef = useRef(autoRefresh);
  autoRefreshRef.current = autoRefresh;

  // Tick every 30s so the relative timestamp stays current.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, []);

  // Schedule the next auto-refresh, resetting any pending timer.
  const scheduleAutoRefresh = () => {
    if (autoRefreshTimer.current) clearTimeout(autoRefreshTimer.current);
    if (!autoRefreshRef.current) return;
    autoRefreshTimer.current = setTimeout(doAutoRefresh, AUTO_REFRESH_MS);
  };

  const doAutoRefresh = async () => {
    if (!autoRefreshRef.current) return;
    try {
      await triggerRefresh();
    } catch (e) {
      console.error('auto-refresh failed', e);
    }
    scheduleAutoRefresh();
  };

  // Restart or stop auto-refresh cycle when toggle changes.
  useEffect(() => {
    if (autoRefresh) {
      scheduleAutoRefresh();
    } else if (autoRefreshTimer.current) {
      clearTimeout(autoRefreshTimer.current);
      autoRefreshTimer.current = null;
    }
    return () => {
      if (autoRefreshTimer.current) clearTimeout(autoRefreshTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh]);

  const toggleAutoRefresh = () => {
    setAutoRefresh((prev) => {
      const next = !prev;
      localStorage.setItem(LS_AUTO_REFRESH, next ? '1' : '0');
      return next;
    });
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
    // Reset auto-refresh timer after manual refresh.
    scheduleAutoRefresh();
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:gap-6 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <ActivityIcon />
          </span>
          <span className="font-semibold tracking-tight">
            Basis &amp; Vol Lab
          </span>
        </div>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 text-sm md:flex">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                'rounded-md px-3 py-1.5 transition-colors ' +
                (isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/60')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            updated {formatRelative(meta.data?.generated_at)}
            {meta.data?.generated_at && isStale(meta.data.generated_at) && (
              <span
                className="ml-1 text-[color:var(--warning)]"
                title="Data may be stale — GitHub Actions cron runs are best-effort and may be delayed"
              >
                ⚠
              </span>
            )}
          </span>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className={
              'inline-flex items-center gap-1.5 rounded-md border border-border ' +
              'bg-card px-2.5 py-1.5 text-xs font-medium text-foreground ' +
              'hover:bg-accent transition-colors disabled:opacity-60'
            }
          >
            <RefreshIcon className={refreshing ? 'animate-spin' : undefined} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <button
            type="button"
            onClick={toggleAutoRefresh}
            title={autoRefresh ? 'Auto-refresh on (5 min)' : 'Auto-refresh off'}
            className={
              'hidden sm:inline-flex items-center gap-1 rounded-md border px-2 py-1.5 text-xs font-medium transition-colors ' +
              (autoRefresh
                ? 'border-primary/40 bg-primary/10 text-primary hover:bg-primary/20'
                : 'border-border bg-card text-muted-foreground hover:bg-accent')
            }
          >
            <span className="relative flex h-2 w-2">
              {autoRefresh && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-50" />
              )}
              <span
                className={
                  'relative inline-flex h-2 w-2 rounded-full ' +
                  (autoRefresh ? 'bg-primary' : 'bg-muted-foreground/40')
                }
              />
            </span>
            Auto
          </button>
          <ThemeToggle />
          {/* Mobile menu toggle */}
          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle navigation"
            className={
              'inline-flex h-9 w-9 items-center justify-center rounded-md ' +
              'border border-border bg-card text-muted-foreground ' +
              'hover:text-foreground hover:bg-accent transition-colors md:hidden'
            }
          >
            {mobileOpen ? <XIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {/* Mobile nav dropdown */}
      {mobileOpen && (
        <nav className="border-t border-border bg-background px-4 pb-4 pt-2 md:hidden">
          <div className="flex flex-col gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  'rounded-md px-3 py-2 text-sm transition-colors ' +
                  (isActive
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <div className="mt-2 px-3 text-xs text-muted-foreground">
            updated {formatRelative(meta.data?.generated_at)}
            {meta.data?.generated_at && isStale(meta.data.generated_at) && (
              <span className="ml-1 text-[color:var(--warning)]">⚠ stale</span>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
