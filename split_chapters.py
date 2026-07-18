#!/usr/bin/env python3
"""Migrate chapter bodies out of chapters.json into chapters/chuong-N.txt files."""

from __future__ import annotations

import json
from pathlib import Path

from crawl import (
    OUT_DIR,
    CHAPTERS_DIR,
    chapter_rel_path,
    regenerate_index,
    write_chapter_text,
)


def main() -> None:
    json_path = OUT_DIR / "chapters.json"
    if not json_path.exists():
        raise SystemExit(f"Missing {json_path}")

    before_size = json_path.stat().st_size
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not data:
        raise SystemExit("chapters.json is empty")

    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    meta = []
    for c in data:
        n = int(c["n"])
        text = c.get("text")
        if not text and c.get("path"):
            p = OUT_DIR / c["path"]
            if p.exists():
                text = p.read_text(encoding="utf-8")
        if not text and c.get("content_html"):
            from bs4 import BeautifulSoup

            text = BeautifulSoup(c["content_html"], "html.parser").get_text(
                "\n", strip=True
            )
        if not text:
            raise SystemExit(f"Chapter {n} has no text/content_html/path to migrate")

        rel = write_chapter_text(n, text)
        meta.append(
            {
                "n": n,
                "title": c.get("title", f"Chương {n}"),
                "story": c.get("story", "Đại Vương Tha Mạng"),
                "url": c.get("url", ""),
                "path": rel,
            }
        )
        print(f"  wrote {rel} ({len(text.strip())} chars)")

    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    after_size = json_path.stat().st_size

    print(f"\nMigrated {len(meta)} chapter(s) → {CHAPTERS_DIR}/")
    print(f"chapters.json: {before_size:,} → {after_size:,} bytes")
    regenerate_index()


if __name__ == "__main__":
    main()
