"use client";

import Link from "next/link";
import { useToc } from "@/components/Sidebar";

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
  const { openToc } = useToc();

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
      <button
        type="button"
        className="reader-nav-link reader-nav-link-muted"
        onClick={openToc}
      >
        Mục lục
      </button>
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
