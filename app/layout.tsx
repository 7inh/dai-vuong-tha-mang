import { Analytics } from "@vercel/analytics/react";
import type { Metadata } from "next";
import { Be_Vietnam_Pro, Literata } from "next/font/google";
import { STORY_TITLE } from "@/lib/types";
import "./globals.css";

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "600"],
  variable: "--sans",
});

const literata = Literata({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "600"],
  variable: "--serif",
});

export const metadata: Metadata = {
  title: `${STORY_TITLE} — Reader`,
  description: "Đọc truyện Đại Vương Tha Mạng offline",
  authors: [{ name: STORY_TITLE }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${beVietnamPro.variable} ${literata.variable}`}>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
