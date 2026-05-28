import type { ReactNode } from 'react';

export function Card({
  children,
  className = '',
  title,
  subtitle,
}: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
}) {
  return (
    <section
      className={
        'rounded-xl border border-border bg-card text-card-foreground ' +
        'shadow-sm transition-colors ' +
        className
      }
    >
      {(title || subtitle) && (
        <header className="px-5 pt-4 pb-2">
          {title && (
            <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
          )}
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </header>
      )}
      <div className="px-5 pb-5 pt-2">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: 'neutral' | 'positive' | 'negative' | 'warning';
}) {
  const toneClass = {
    neutral: 'text-foreground',
    positive: 'text-[color:var(--positive)]',
    negative: 'text-[color:var(--negative)]',
    warning: 'text-[color:var(--warning)]',
  }[tone];
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={`font-mono text-lg tabular-nums sm:text-xl ${toneClass}`}
      >
        {value}
      </span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}
