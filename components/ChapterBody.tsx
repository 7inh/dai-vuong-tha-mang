import type { ChapterMeta } from "@/lib/types";

type ChapterBodyProps = {
  paragraphs: string[];
};

export function ChapterBody({ paragraphs }: ChapterBodyProps) {
  return (
    <div className="chapter-body">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

type ChapterBlockProps = {
  chapter: ChapterMeta & { paragraphs: string[] };
  headingLevel?: "h1" | "h2";
};

export function ChapterBlock({ chapter, headingLevel = "h2" }: ChapterBlockProps) {
  const Heading = headingLevel;
  return (
    <section className="chapter-block" id={`chuong-${chapter.n}`}>
      <Heading className="chapter-heading">{chapter.title}</Heading>
      <ChapterBody paragraphs={chapter.paragraphs} />
    </section>
  );
}
