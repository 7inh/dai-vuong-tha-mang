import { Suspense } from "react";
import { ReaderShell } from "@/components/Sidebar";
import { getChapterList } from "@/lib/chapters";

export default async function ReaderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const chapters = await getChapterList();

  return (
    <Suspense fallback={<div className="layout"><main className="main">Đang tải…</main></div>}>
      <ReaderShell chapters={chapters}>{children}</ReaderShell>
    </Suspense>
  );
}
