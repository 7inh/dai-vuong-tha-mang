import { notFound } from "next/navigation";
import { ChapterBody } from "@/components/ChapterBody";
import { ReaderNav } from "@/components/ReaderNav";
import {
  getAdjacentChapterNumbers,
  getChapter,
  getChapterList,
} from "@/lib/chapters";
import { STORY_TITLE } from "@/lib/types";
import type { Metadata } from "next";

type PageProps = {
  params: Promise<{ n: string }>;
};

export async function generateStaticParams() {
  const chapters = await getChapterList();
  return chapters.map((c) => ({ n: String(c.n) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { n } = await params;
  try {
    const chapter = await getChapter(Number(n));
    return {
      title: `${chapter.title} — ${STORY_TITLE}`,
    };
  } catch {
    return { title: STORY_TITLE };
  }
}

export default async function ChapterPage({ params }: PageProps) {
  const { n: nParam } = await params;
  const n = Number(nParam);
  if (Number.isNaN(n)) notFound();

  let chapter;
  try {
    chapter = await getChapter(n);
  } catch {
    notFound();
  }

  const { prev, next } = await getAdjacentChapterNumbers(n);

  const prevLink =
    prev !== null ? { href: `/chuong/${prev}`, label: "← Trước" } : null;
  const nextLink =
    next !== null ? { href: `/chuong/${next}`, label: "Sau →" } : null;

  return (
    <>
      <ReaderNav prev={prevLink} next={nextLink} summary={chapter.title} />
      <article>
        <h1 className="chapter-heading">{chapter.title}</h1>
        <ChapterBody paragraphs={chapter.paragraphs} />
      </article>
    </>
  );
}
