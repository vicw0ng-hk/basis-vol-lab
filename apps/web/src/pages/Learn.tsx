import { useEffect } from 'react';
import { NavLink, useParams } from 'react-router-dom';
import { Markdown } from '../components/Markdown';
import { LECTURES, findLecture } from '../lib/lectures';

function Sidebar({ activeSlug }: { activeSlug: string }) {
  const numbered = LECTURES.filter((l) => l.slug !== 'README');
  return (
    <aside className="lg:sticky lg:top-20 lg:self-start">
      <nav className="rounded-xl border border-border bg-card p-3 text-sm">
        <NavLink
          to="/learn"
          end
          className={({ isActive }) =>
            'block rounded-md px-3 py-1.5 transition-colors ' +
            (isActive || activeSlug === 'README'
              ? 'bg-accent text-accent-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/60')
          }
        >
          Course overview
        </NavLink>
        <div className="mt-2 mb-1 px-3 text-[11px] uppercase tracking-wider text-muted-foreground">
          Lectures
        </div>
        <ol className="space-y-0.5">
          {numbered.map((l) => (
            <li key={l.slug}>
              <NavLink
                to={`/learn/${l.slug}`}
                className={({ isActive }) =>
                  'flex gap-2 rounded-md px-3 py-1.5 transition-colors ' +
                  (isActive
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60')
                }
              >
                <span className="font-mono tabular-nums text-xs opacity-70">
                  {String(l.number).padStart(2, '0')}
                </span>
                <span>{l.title}</span>
              </NavLink>
            </li>
          ))}
        </ol>
      </nav>
    </aside>
  );
}

export default function LearnPage() {
  const { slug } = useParams<{ slug?: string }>();
  const activeSlug = slug ?? 'README';
  const lecture = findLecture(activeSlug);

  // Scroll to top (or to a #hash) when the slug changes.
  useEffect(() => {
    if (window.location.hash) {
      const el = document.getElementById(window.location.hash.slice(1));
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
        return;
      }
    }
    window.scrollTo({ top: 0 });
  }, [activeSlug]);

  return (
    <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
      <Sidebar activeSlug={activeSlug} />
      <article className="min-w-0 rounded-xl border border-border bg-card p-6 sm:p-8">
        {lecture ? (
          <Markdown source={lecture.source} />
        ) : (
          <div className="text-sm text-muted-foreground">Lecture not found.</div>
        )}
      </article>
    </div>
  );
}
