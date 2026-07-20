import { readFile } from "fs/promises";
import path from "path";
import type { Chapter, ChapterMeta } from "./types";

let chapterListCache: ChapterMeta[] | null = null;

function rootPath(...segments: string[]) {
  return path.join(process.cwd(), ...segments);
}

function textToParagraphs(text: string): string[] {
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export async function getChapterList(): Promise<ChapterMeta[]> {
  if (chapterListCache) {
    return chapterListCache;
  }

  const raw = await readFile(rootPath("chapters.json"), "utf-8");
  const data = JSON.parse(raw) as ChapterMeta[];
  chapterListCache = [...data].sort((a, b) => a.n - b.n);
  return chapterListCache;
}

export async function getChapter(n: number): Promise<Chapter> {
  const list = await getChapterList();
  const meta = list.find((c) => c.n === n);
  if (!meta) {
    throw new Error(`Chapter ${n} not found`);
  }

  const text = await readFile(rootPath(meta.path), "utf-8");
  return {
    ...meta,
    paragraphs: textToParagraphs(text),
  };
}

export async function getChapterRange(from: number, to: number): Promise<Chapter[]> {
  const list = await getChapterList();
  const lo = Math.min(from, to);
  const hi = Math.max(from, to);
  const selected = list.filter((c) => c.n >= lo && c.n <= hi);
  return Promise.all(selected.map((c) => getChapter(c.n)));
}

export async function getAdjacentChapterNumbers(n: number): Promise<{
  prev: number | null;
  next: number | null;
}> {
  const list = await getChapterList();
  const idx = list.findIndex((c) => c.n === n);
  if (idx === -1) {
    return { prev: null, next: null };
  }
  return {
    prev: idx > 0 ? list[idx - 1].n : null,
    next: idx < list.length - 1 ? list[idx + 1].n : null,
  };
}

export function clampChapterRange(
  list: ChapterMeta[],
  from: number,
  to: number
): { from: number; to: number } {
  if (!list.length) {
    return { from: 1, to: 1 };
  }

  const nums = new Set(list.map((c) => c.n));
  let lo = Math.min(from, to);
  let hi = Math.max(from, to);

  if (!nums.has(lo)) lo = list[0].n;
  if (!nums.has(hi)) hi = list[list.length - 1].n;

  return { from: lo, to: hi };
}
