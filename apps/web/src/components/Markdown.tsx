import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import 'katex/dist/katex.min.css';

/**
 * Renders a Markdown string as the lecture body.
 *
 * - GFM: tables, task lists, strikethrough.
 * - KaTeX: `$...$` and `$$...$$` math.
 * - Custom <a>: inter-lecture `.md` links route inside the app; in-repo
 *   source-code links are rendered as inline code (no broken navigation);
 *   external links open in a new tab.
 */
export function Markdown({ source }: { source: string }) {
  return (
    <div className="lecture-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          a({ href, children, ...rest }) {
            const url = href ?? '';
            // External links: open in a new tab.
            if (/^https?:\/\//i.test(url)) {
              return (
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer noopener"
                  {...rest}
                >
                  {children}
                </a>
              );
            }
            // Sibling lecture in docs/analytics: route in-app.
            const lectureMatch = url.match(/([A-Za-z0-9_-]+)\.md(#.*)?$/);
            const isAnalyticsRelative =
              lectureMatch &&
              !url.includes('/packages/') &&
              !url.includes('/apps/');
            if (isAnalyticsRelative) {
              const slug = lectureMatch[1];
              const hash = lectureMatch[2] ?? '';
              return <Link to={`/learn/${slug}${hash}`}>{children}</Link>;
            }
            // Source-code or other in-repo paths: not navigable from the
            // browser. Fall back to a non-link span styled like inline code
            // so text still flows naturally.
            return (
              <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
                {children}
              </code>
            );
          },
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
