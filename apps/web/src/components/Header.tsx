import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { triggerRefresh, useArtifact, type Meta } from '../lib/api';
import { formatRelative } from '../lib/format';
import { ThemeToggle } from './ThemeToggle';

const NAV = [
  { to: '/', label: 'Overview', end: true },
  { to: '/vol', label: 'Volatility' },
  { to: '/carry', label: 'Carry' },
  { to: '/signals', label: 'Signals' },
  { to: '/learn', label: 'Learn' },
];

function ActivityIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M8 16H3v5" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" x2="20" y1="12" y2="12" />
      <line x1="4" x2="20" y1="6" y2="6" />
      <line x1="4" x2="20" y1="18" y2="18" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

export function Header() {
  const meta = useArtifact<Meta>('/api/meta');
  const [refreshing, setRefreshing] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:gap-6 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <ActivityIcon />
          </span>
          <span className="font-semibold tracking-tight">Basis &amp; Vol Lab</span>
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
          </div>
        </nav>
      )}
    </header>
  );
}
