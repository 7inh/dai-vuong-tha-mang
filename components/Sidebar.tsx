"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { ChapterMeta } from "@/lib/types";

type SidebarProps = {
  chapters: ChapterMeta[];
  open: boolean;
  onClose: () => void;
};

function SidebarPanel({ chapters, open, onClose }: SidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [from, setFrom] = useState(String(chapters[0]?.n ?? 1));
  const [to, setTo] = useState(String(chapters[0]?.n ?? 1));

  const chapterMatch = pathname.match(/^\/chuong\/(\d+)/);
  const activeChapter = chapterMatch ? Number(chapterMatch[1]) : null;

  let rangeFrom: number | null = null;
  let rangeTo: number | null = null;
  if (pathname === "/doc") {
    const fromParam = Number(searchParams.get("from"));
    const toParam = Number(searchParams.get("to"));
    if (!Number.isNaN(fromParam) && !Number.isNaN(toParam)) {
      rangeFrom = Math.min(fromParam, toParam);
      rangeTo = Math.max(fromParam, toParam);
    }
  }

  function isActive(n: number) {
    if (activeChapter !== null) return activeChapter === n;
    if (rangeFrom !== null && rangeTo !== null) return n >= rangeFrom && n <= rangeTo;
    return false;
  }

  function goRange(singleOnly: boolean) {
    const fromN = Number(from);
    const toN = singleOnly ? fromN : Number(to);
    const lo = Math.min(fromN, toN);
    const hi = Math.max(fromN, toN);
    onClose();
    if (singleOnly || lo === hi) {
      router.push(`/chuong/${lo}`);
    } else {
      router.push(`/doc?from=${lo}&to=${hi}`);
    }
  }

  return (
    <aside className={`sidebar${open ? " open" : ""}`} id="sidebar">
      <h1>Đại Vương Tha Mạng</h1>
      <div className="meta">{chapters.length} chương · đọc offline</div>
      <div className="range-box">
        <div className="label">Chọn khoảng chương</div>
        <div className="range-row">
          <label htmlFor="fromSelect">Từ chương</label>
          <select
            id="fromSelect"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              if (Number(e.target.value) > Number(to)) {
                setTo(e.target.value);
              }
            }}
          >
            {chapters.map((c) => (
              <option key={c.n} value={c.n}>
                {c.title}
              </option>
            ))}
          </select>
        </div>
        <div className="range-row">
          <label htmlFor="toSelect">Đến chương</label>
          <select
            id="toSelect"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              if (Number(e.target.value) < Number(from)) {
                setFrom(e.target.value);
              }
            }}
          >
            {chapters.map((c) => (
              <option key={c.n} value={c.n}>
                {c.title}
              </option>
            ))}
          </select>
        </div>
        <div className="actions">
          <button type="button" onClick={() => goRange(false)}>
            Xem khoảng
          </button>
          <button type="button" className="secondary" onClick={() => goRange(true)}>
            1 chương
          </button>
        </div>
      </div>
      <nav className="toc" id="toc">
        {chapters.map((c) => (
          <Link
            key={c.n}
            href={`/chuong/${c.n}`}
            className={`toc-item${isActive(c.n) ? " active" : ""}`}
            onClick={onClose}
          >
            {c.title}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

export function ReaderShell({
  chapters,
  children,
}: {
  chapters: ChapterMeta[];
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="layout">
      <SidebarPanel chapters={chapters} open={open} onClose={() => setOpen(false)} />
      <main className="main">
        <button
          type="button"
          className="menu-toggle"
          onClick={() => setOpen((value) => !value)}
        >
          Mục lục
        </button>
        {children}
      </main>
    </div>
  );
}
