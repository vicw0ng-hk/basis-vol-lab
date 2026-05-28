import type { ReactNode } from 'react';

export function PageState({
  loading,
  error,
  children,
  empty,
}: {
  loading: boolean;
  error: string | null;
  children: ReactNode;
  empty?: boolean;
}) {
  if (loading) {
    return (
      <div className="grid place-items-center py-24 text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (error) {
    const isUnavailable =
      error.includes('503') || error.includes('502') || error.includes('504');
    if (isUnavailable) {
      return (
        <div className="grid place-items-center py-24 text-sm text-muted-foreground">
          <div className="text-center space-y-2">
            <div className="animate-pulse">Loading data…</div>
            <div className="text-xs">
              The API is warming up. Refresh in a few seconds.
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="rounded-lg border border-[color:var(--negative)]/40 bg-[color:var(--negative)]/10 p-6 text-sm">
        <div className="font-semibold mb-1">Failed to load data</div>
        <div className="font-mono text-xs text-muted-foreground">{error}</div>
        <p className="mt-3 text-xs text-muted-foreground">
          Tip: run <code>mise run snapshot</code> first to generate the
          artifacts the API serves.
        </p>
      </div>
    );
  }
  if (empty) {
    return (
      <div className="grid place-items-center py-24 text-sm text-muted-foreground">
        No data available yet.
      </div>
    );
  }
  return <>{children}</>;
}
