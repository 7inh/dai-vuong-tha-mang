#!/usr/bin/env python3
"""Extract chapters from a MOBI ebook and replace local chapters/*.txt files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import unicodedata
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import mobi

ROOT = Path(__file__).resolve().parent
DEFAULT_MOBI = Path(
    "/Users/leelinh/Library/Mobile Documents/com~apple~CloudDocs/dai-vuong-tha-mang.mobi"
)
CHAPTERS_DIR = ROOT / "chapters"
CHAPTERS_JSON = ROOT / "chapters.json"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "br":
            self.parts.append("\n")
        elif tag in ("p", "div", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in ("p", "div", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    text = unescape("".join(parser.parts))
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse whitespace within lines; keep paragraph breaks.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines).strip()


def parse_toc_filepos(toc: str) -> dict[int, str]:
    """Map chapter number -> filepos id from toc.ncx."""
    out: dict[int, str] = {}
    for m in re.finditer(
        r"<text>\s*Chuong\s*(\d+)\s*</text>\s*</navLabel>\s*"
        r'<content\s+src="book\.html#(filepos\d+)"\s*/>',
        toc,
        re.I | re.S,
    ):
        out[int(m.group(1))] = m.group(2)
    return out


def extract_chapter_body(html: str, toc_map: dict[int, str], n: int) -> tuple[str, str]:
    """Return (title, body) for chapter n. Body has no title line."""
    fp = toc_map.get(n)
    if not fp:
        raise KeyError(f"Chapter {n} not found in MOBI TOC")
    fp_next = toc_map.get(n + 1)
    start = html.find(f'id="{fp}"')
    if start < 0:
        raise KeyError(f"Anchor id={fp!r} missing for chapter {n}")
    end = html.find(f'id="{fp_next}"') if fp_next else len(html)
    if end < 0:
        end = len(html)

    frag = html[start:end]
    frag = re.sub(r"^[^>]*>", "", frag, count=1)
    text = html_to_text(frag)

    title = f"Chương {n}"
    body = text
    m = re.match(rf"^{n}\s*[,:：.\-–—]\s*(.+?)(?:\n|$)", text)
    if m:
        raw_title = m.group(1).strip()
        # Title-case lightly for chapters.json style: keep as extracted, prefix Chương
        title = f"Chương {n} : {raw_title[0].upper() + raw_title[1:]}" if raw_title else title
        body = text[m.end() :].strip()

    return title, body


def unpack_mobi(mobi_path: Path, work_dir: Path) -> tuple[str, dict[int, str]]:
    # mobi.extract writes to a system temp dir; copy book.html + toc into work_dir
    tmp, _html_path = mobi.extract(str(mobi_path))
    src = Path(tmp) / "mobi7"
    dest = work_dir / "mobi7"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    html = (dest / "book.html").read_text(encoding="utf-8", errors="replace")
    toc = (dest / "toc.ncx").read_text(encoding="utf-8", errors="replace")
    return html, parse_toc_filepos(toc)


def update_chapters_json(updates: dict[int, str]) -> None:
    if not CHAPTERS_JSON.exists():
        return
    meta = json.loads(CHAPTERS_JSON.read_text(encoding="utf-8"))
    by_n = {int(c["n"]): c for c in meta}
    for n, title in updates.items():
        if n in by_n:
            by_n[n]["title"] = title
        else:
            by_n[n] = {
                "n": n,
                "title": title,
                "story": "Đại Vương Tha Mạng",
                "path": f"chapters/chuong-{n}.txt",
            }
    ordered = [by_n[k] for k in sorted(by_n)]
    CHAPTERS_JSON.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobi", type=Path, default=DEFAULT_MOBI)
    parser.add_argument("--from", dest="from_n", type=int, default=231)
    parser.add_argument("--to", dest="to_n", type=int, default=249)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and print stats without writing files",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not update titles in chapters.json",
    )
    args = parser.parse_args()

    if not args.mobi.exists():
        raise SystemExit(f"MOBI not found: {args.mobi}")

    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mobi_chapters_") as tmp:
        html, toc_map = unpack_mobi(args.mobi, Path(tmp))
        title_updates: dict[int, str] = {}
        for n in range(args.from_n, args.to_n + 1):
            title, body = extract_chapter_body(html, toc_map, n)
            out = CHAPTERS_DIR / f"chuong-{n}.txt"
            print(f"chuong-{n}: {len(body)} chars, title={title!r}")
            if args.dry_run:
                continue
            out.write_text(body + "\n", encoding="utf-8")
            title_updates[n] = title

        if not args.dry_run and not args.no_json and title_updates:
            update_chapters_json(title_updates)
            print(f"Updated titles in {CHAPTERS_JSON.name}")

    print(f"Done: chapters {args.from_n}–{args.to_n}")


if __name__ == "__main__":
    main()
