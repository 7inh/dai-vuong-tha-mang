import { ChapterBlock } from "@/components/ChapterBody";
import { ReaderNav } from "@/components/ReaderNav";
import {
  clampChapterRange,
  getChapterList,
  getChapterRange,
} from "@/lib/chapters";
import { STORY_TITLE } from "@/lib/types";
import type { Metadata } from "next";

type PageProps = {
  searchParams: Promise<{ from?: string; to?: string }>;
};

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  const params = await searchParams;
  const from = Number(params.from ?? 1);
  const to = Number(params.to ?? from);
  if (from === to) {
    return { title: STORY_TITLE };
  }
  return {
    title: `Chương ${Math.min(from, to)} → ${Math.max(from, to)} — ${STORY_TITLE}`,
  };
}

export default async function DocRangePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const list = await getChapterList();
  const fromRaw = Number(params.from ?? list[0]?.n ?? 1);
  const toRaw = Number(params.to ?? fromRaw);
  const { from, to } = clampChapterRange(list, fromRaw, toRaw);
  const chapters = await getChapterRange(from, to);
  const count = chapters.length;

  const firstIdx = list.findIndex((c) => c.n === from);
  const lastIdx = list.findIndex((c) => c.n === to);
  const span = to - from;

  let prevRange: { from: number; to: number } | null = null;
  if (firstIdx > 0) {
    const newTo = list[firstIdx - 1].n;
    const newFromIdx = Math.max(0, firstIdx - 1 - span);
    prevRange = { from: list[newFromIdx].n, to: newTo };
  }

  let nextRange: { from: number; to: number } | null = null;
  if (lastIdx < list.length - 1) {
    const newFrom = list[lastIdx + 1].n;
    const newToIdx = Math.min(list.length - 1, lastIdx + 1 + span);
    nextRange = { from: newFrom, to: list[newToIdx].n };
  }

  const summary =
    count === 1
      ? chapters[0].title
      : `Chương ${from} → ${to} (${count} chương)`;

  const prevLink = prevRange
    ? {
        href: `/doc?from=${prevRange.from}&to=${prevRange.to}`,
        label: "← Trước",
      }
    : null;
  const nextLink = nextRange
    ? {
        href: `/doc?from=${nextRange.from}&to=${nextRange.to}`,
        label: "Sau →",
      }
    : null;

  return (
    <>
      <ReaderNav prev={prevLink} next={nextLink} summary={summary} />
      {chapters.map((chapter) => (
        <ChapterBlock key={chapter.n} chapter={chapter} headingLevel="h2" />
      ))}
    </>
  );
}
