import { useTheme } from '../lib/theme';
import { MoonIcon, SunIcon } from './Icons';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={
        'inline-flex h-9 w-9 items-center justify-center rounded-md ' +
        'border border-border bg-card text-muted-foreground ' +
        'hover:text-foreground hover:bg-accent transition-colors'
      }
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
