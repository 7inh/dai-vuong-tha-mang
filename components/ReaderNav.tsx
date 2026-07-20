import Link from "next/link";

type NavLink = {
  href: string;
  label: string;
};

type ReaderNavProps = {
  prev: NavLink | null;
  next: NavLink | null;
  summary?: string;
};

export function ReaderNav({ prev, next, summary }: ReaderNavProps) {
  return (
    <nav className="reader-nav" aria-label="Điều hướng chương">
      {prev ? (
        <Link className="reader-nav-link" href={prev.href}>
          {prev.label}
        </Link>
      ) : (
        <span className="reader-nav-link disabled">← Trước</span>
      )}
      {summary ? <span className="range-summary">{summary}</span> : null}
      <Link className="reader-nav-link reader-nav-link-muted" href="/chuong/1">
        Mục lục
      </Link>
      {next ? (
        <Link className="reader-nav-link" href={next.href}>
          {next.label}
        </Link>
      ) : (
        <span className="reader-nav-link disabled">Sau →</span>
      )}
    </nav>
  );
}
