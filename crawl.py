#!/usr/bin/env python3
"""Crawl Đại Vương Tha Mạng chapters into a local HTML reader."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Standalone "." (or ".." etc.) used as empty paragraph spacers on the source site
_DOT_ONLY = re.compile(r"^\.+$")
_BR_DOT_BR = re.compile(
    r"(?:<br\s*/?>\s*)+\.+(?:\s*<br\s*/?>)+",
    re.IGNORECASE,
)
_MULTI_BR = re.compile(r"(?:<br\s*/?>\s*){3,}", re.IGNORECASE)
# Uploader watermark that sometimes prefixes chapter HTML
_POSTER_LINE = re.compile(
    r"Người\s*đăng\s*:\s*๖ۣۜJet\s*๖ۣۜBlack",
    re.IGNORECASE,
)
_POSTER_TAG = re.compile(
    r"<\s*p\s*>\s*Người\s*đăng\s*:\s*๖ۣۜJet\s*๖ۣۜBlack\s*<\s*/\s*p\s*>\s*",
    re.IGNORECASE,
)

BASE_URL = "https://truyenmoiss.org/dai-vuong-tha-mang/chuong-{n}"
OUT_DIR = Path(__file__).resolve().parent
CHAPTERS_DIR = OUT_DIR / "chapters"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}
DELAY_SEC = 2.0  # pause between requests to avoid stressing the source server


def chapter_rel_path(n: int) -> str:
    return f"chapters/chuong-{n}.txt"


def chapter_abs_path(n: int) -> Path:
    return OUT_DIR / chapter_rel_path(n)


def write_chapter_text(n: int, text: str) -> str:
    """Write chapter body to chapters/chuong-N.txt; return relative path."""
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    rel = chapter_rel_path(n)
    (OUT_DIR / rel).write_text(text.strip() + "\n", encoding="utf-8")
    return rel


def read_chapter_text(rel_or_n: str | int) -> str:
    if isinstance(rel_or_n, int):
        path = chapter_abs_path(rel_or_n)
    else:
        path = OUT_DIR / rel_or_n
    return path.read_text(encoding="utf-8").strip()


def clean_chapter_html(article: BeautifulSoup) -> str:
    """Remove ads/scripts and blank paragraphs that are only a single '.'."""
    for tag in article.select("script, style, iframe, noscript, .ads, .advertisement"):
        tag.decompose()

    # Drop uploader watermark paragraphs (Người đăng: Jet Black)
    for tag in list(article.find_all(["p", "div", "span"])):
        text = tag.get_text(" ", strip=True)
        if _POSTER_LINE.fullmatch(text):
            tag.decompose()
            continue
        if _DOT_ONLY.fullmatch(text):
            tag.decompose()

    # Drop bare text nodes that are only dots (between <br> tags)
    for node in list(article.find_all(string=True)):
        raw = node.strip()
        if _DOT_ONLY.fullmatch(raw) or _POSTER_LINE.fullmatch(raw):
            node.extract()

    content_html = "".join(str(child) for child in article.children).strip()
    if not content_html:
        content_html = article.decode_contents().strip()

    # Collapse leftover <br/>.<br/> spacers the parser may miss
    content_html = _POSTER_TAG.sub("", content_html)
    content_html = _POSTER_LINE.sub("", content_html)
    content_html = _BR_DOT_BR.sub("<br/><br/>", content_html)
    content_html = _MULTI_BR.sub("<br/><br/>", content_html)
    return content_html


def fetch_chapter(n: int, session: requests.Session) -> dict:
    url = BASE_URL.format(n=n)
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.select_one("a.chapter-title")
            title = title_el.get_text(" ", strip=True) if title_el else f"Chương {n}"

            story_el = soup.select_one("a.truyen-title")
            story = story_el.get_text(strip=True) if story_el else "Đại Vương Tha Mạng"

            article = soup.select_one("article.chapter-content")
            if not article:
                raise ValueError(f"No article.chapter-content on {url}")

            content_html = clean_chapter_html(article)
            text_preview = BeautifulSoup(content_html, "html.parser").get_text(
                "\n", strip=True
            )
            if len(text_preview) < 50:
                raise ValueError(f"Chapter {n} content too short ({len(text_preview)} chars)")

            return {
                "n": n,
                "title": title,
                "story": story,
                "url": url,
                "content_html": content_html,
                "text": text_preview,
            }
        except Exception as e:
            last_err = e
            if attempt == 0:
                print(f"  retry chapter {n}: {e}")
                time.sleep(1.5)
    raise RuntimeError(f"Failed chapter {n}: {last_err}") from last_err


def load_existing_chapters() -> dict[int, dict]:
    path = OUT_DIR / "chapters.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    by_n: dict[int, dict] = {}
    for c in data:
        n = int(c["n"])
        entry = {
            "n": n,
            "title": c.get("title", f"Chương {n}"),
            "story": c.get("story", "Đại Vương Tha Mạng"),
            "url": c.get("url", BASE_URL.format(n=n)),
            "path": c.get("path") or chapter_rel_path(n),
        }
        # Prefer on-disk txt; fall back to legacy embedded fields during migration
        txt_path = OUT_DIR / entry["path"]
        if txt_path.exists():
            entry["text"] = read_chapter_text(entry["path"])
        elif c.get("text"):
            entry["text"] = c["text"]
        if c.get("content_html") and "text" not in entry:
            entry["content_html"] = c["content_html"]
        by_n[n] = entry
    return by_n


def serialize_chapters(chapters: list[dict]) -> list[dict]:
    out = []
    for c in chapters:
        n = int(c["n"])
        text = c.get("text")
        if text is None and c.get("path"):
            text = read_chapter_text(c["path"])
        if text is None and c.get("content_html"):
            text = BeautifulSoup(c["content_html"], "html.parser").get_text(
                "\n", strip=True
            )
        if text is None:
            raise ValueError(f"Chapter {n} has no text to save")
        rel = write_chapter_text(n, text)
        out.append(
            {
                "n": n,
                "title": c["title"],
                "story": c.get("story", "Đại Vương Tha Mạng"),
                "url": c.get("url", BASE_URL.format(n=n)),
                "path": rel,
            }
        )
    return out


def save_library(chapters: list[dict], story_title: str | None = None) -> None:
    """Write chapter txt files + chapters.json. Does not touch index.html (static reader)."""
    del story_title  # kept for call-site compatibility
    meta = serialize_chapters(chapters)
    for m, ch in zip(meta, chapters):
        ch["path"] = m["path"]
        ch["text"] = read_chapter_text(m["path"])
    (OUT_DIR / "chapters.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def sync_chapters_json_from_disk() -> None:
    """Rebuild chapters.json from existing chapters/*.txt (titles from prior json when possible)."""
    by_n = load_existing_chapters()
    for path in sorted(CHAPTERS_DIR.glob("chuong-*.txt")):
        m = re.search(r"chuong-(\d+)\.txt$", path.name)
        if not m:
            continue
        n = int(m.group(1))
        if n in by_n:
            continue
        by_n[n] = {
            "n": n,
            "title": f"Chương {n}",
            "story": "Đại Vương Tha Mạng",
            "url": BASE_URL.format(n=n),
            "path": chapter_rel_path(n),
            "text": read_chapter_text(n),
        }
    chapters = [by_n[k] for k in sorted(by_n)]
    if not chapters:
        raise SystemExit("No chapters to sync")
    save_chapters_json(chapters)
    print(f"Synced chapters.json with {len(chapters)} chapter(s)")


def save_chapters_json(chapters: list[dict]) -> None:
    """Persist chapter metadata only (txt files already on disk)."""
    meta = []
    for c in chapters:
        n = int(c["n"])
        rel = c.get("path") or chapter_rel_path(n)
        meta.append(
            {
                "n": n,
                "title": c["title"],
                "story": c.get("story", "Đại Vương Tha Mạng"),
                "url": c.get("url", BASE_URL.format(n=n)),
                "path": rel,
            }
        )
    (OUT_DIR / "chapters.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Đại Vương Tha Mạng chapters")
    parser.add_argument("--start", type=int, default=1, help="First chapter number")
    parser.add_argument("--end", type=int, default=25, help="Last chapter number (inclusive)")
    parser.add_argument(
        "--delay",
        type=float,
        default=DELAY_SEC,
        help=f"Seconds to wait between chapter requests (default {DELAY_SEC})",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Replace chapters.json instead of merging with existing chapters",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even when chapter txt already exists",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Update chapters.json every N newly fetched chapters (default 10)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Only rebuild chapters.json from chapters/*.txt (no fetch)",
    )
    args = parser.parse_args()

    if args.sync:
        sync_chapters_json_from_disk()
        return

    if args.start < 1 or args.end < args.start:
        raise SystemExit("Invalid --start/--end range")
    if args.delay < 0:
        raise SystemExit("--delay must be >= 0")

    by_n = {} if args.no_merge else load_existing_chapters()
    if by_n and not args.no_merge:
        print(f"Merging with {len(by_n)} existing chapter(s)")

    session = requests.Session()
    story_title = "Đại Vương Tha Mạng"
    total = args.end - args.start + 1
    fetched = 0
    skipped = 0
    failed: list[int] = []

    for i, n in enumerate(range(args.start, args.end + 1), start=1):
        txt_path = chapter_abs_path(n)
        if not args.force and txt_path.exists() and txt_path.stat().st_size > 50:
            if n not in by_n:
                text = read_chapter_text(n)
                by_n[n] = {
                    "n": n,
                    "title": f"Chương {n}",
                    "story": story_title,
                    "url": BASE_URL.format(n=n),
                    "path": chapter_rel_path(n),
                    "text": text,
                }
            skipped += 1
            print(f"[{i}/{total}] Skip chapter {n} (already on disk)")
            continue

        print(f"[{i}/{total}] Fetching chapter {n} (delay={args.delay}s)...")
        try:
            ch = fetch_chapter(n, session)
        except Exception as e:  # noqa: BLE001 — keep going on long runs
            failed.append(n)
            print(f"  FAIL chapter {n}: {e}")
            if n < args.end:
                time.sleep(args.delay)
            continue

        rel = write_chapter_text(n, ch["text"])
        ch["path"] = rel
        by_n[n] = ch
        story_title = ch["story"]
        fetched += 1
        print(f"  OK: {ch['title']} ({len(ch['text'])} chars)")

        if args.checkpoint_every > 0 and fetched % args.checkpoint_every == 0:
            chapters_ckpt = [by_n[k] for k in sorted(by_n)]
            save_chapters_json(chapters_ckpt)
            print(f"  checkpoint: chapters.json ({len(chapters_ckpt)} chapters)")

        if n < args.end:
            print(f"  waiting {args.delay}s...")
            time.sleep(args.delay)

    chapters = [by_n[k] for k in sorted(by_n)]
    if chapters:
        story_title = chapters[0].get("story") or story_title

    save_library(chapters, story_title)

    print(f"\nWrote {OUT_DIR / 'chapters.json'}")
    print(f"Wrote chapter text under {CHAPTERS_DIR}/")
    print(f"(index.html is static — open it to read; it lazy-loads chapters/*.txt)")
    print(
        f"Crawled: {args.start}–{args.end}; fetched={fetched} skipped={skipped} "
        f"failed={len(failed)}; library now has {len(chapters)} chapter(s)"
    )
    if failed:
        print(f"Failed chapters: {failed}")


if __name__ == "__main__":
    main()
