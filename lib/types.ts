export type ChapterMeta = {
  n: number;
  title: string;
  story: string;
  url: string;
  path: string;
};

export type Chapter = ChapterMeta & {
  paragraphs: string[];
};

export const STORY_TITLE = "Đại Vương Tha Mạng";
