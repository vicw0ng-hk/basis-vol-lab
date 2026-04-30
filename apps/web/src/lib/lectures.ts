// Build-time markdown bundle for the Learn page.

const modules = import.meta.glob('../../../../docs/analytics/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

export interface Lecture {
  slug: string;
  filename: string;
  number: number | null;
  title: string;
  source: string;
}

function deriveTitle(source: string, fallback: string): string {
  const match = source.match(/^#\s+(.+)$/m);
  if (!match) return fallback;
  return match[1].replace(/^Lecture\s+\d+\s*[—-]\s*/, '').trim();
}

function buildLecture(path: string, source: string): Lecture {
  const filename = path.split('/').pop()!;
  const slug = filename.replace(/\.md$/, '');
  const numMatch = slug.match(/^(\d+)-/);
  const number = numMatch ? parseInt(numMatch[1], 10) : null;
  const fallback = slug.replace(/^\d+-/, '').replace(/-/g, ' ');
  return {
    slug,
    filename,
    number,
    title: deriveTitle(source, fallback),
    source,
  };
}

export const LECTURES: Lecture[] = Object.entries(modules)
  .map(([path, source]) => buildLecture(path, source))
  .sort((a, b) => {
    if (a.slug === 'README') return -1;
    if (b.slug === 'README') return 1;
    return (a.number ?? 0) - (b.number ?? 0);
  });

export function findLecture(slug: string): Lecture | undefined {
  return LECTURES.find((l) => l.slug === slug);
}
