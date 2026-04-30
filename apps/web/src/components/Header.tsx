import { Activity, RefreshCw } from 'lucide-react';
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

export function Header() {
  const meta = useArtifact<Meta>('/api/meta');
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
      meta.refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <Activity size={15} strokeWidth={2.5} />
          </span>
          <span className="font-semibold tracking-tight">Basis &amp; Vol Lab</span>
        </div>

        <nav className="flex items-center gap-1 text-sm">
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

        <div className="ml-auto flex items-center gap-3">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            updated {formatRelative(meta.data?.generated_at)}
          </span>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className={
              'inline-flex items-center gap-1.5 rounded-md border border-border ' +
              'bg-card px-3 py-1.5 text-xs font-medium text-foreground ' +
              'hover:bg-accent transition-colors disabled:opacity-60'
            }
          >
            <RefreshCw
              size={13}
              className={refreshing ? 'animate-spin' : undefined}
            />
            Refresh
          </button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
