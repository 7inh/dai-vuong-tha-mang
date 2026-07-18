#!/usr/bin/env python3
"""Crawl Đại Vương Tha Mạng chapters into a local HTML reader."""

from __future__ import annotations

import argparse
import json
import re
import time
from html import escape
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


def text_to_html(text: str) -> str:
    """Convert plain chapter text into simple paragraph HTML for the reader."""
    text = (text or "").strip()
    if not text:
        return ""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paras) <= 1 and "\n" in text:
        paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        paras = [text]
    return "".join(
        f"<p>{escape(p).replace(chr(10), '<br/>')}</p>" for p in paras
    )


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


def chapter_body_html(ch: dict) -> str:
    if ch.get("content_html"):
        return ch["content_html"]
    text = ch.get("text")
    if text is None and ch.get("path"):
        text = read_chapter_text(ch["path"])
    return text_to_html(text or "")


def build_index_html(chapters: list[dict], story_title: str) -> str:
    chapters_json = json.dumps(
        [
            {
                "n": c["n"],
                "title": c["title"],
                "content_html": chapter_body_html(c),
            }
            for c in chapters
        ],
        ensure_ascii=False,
    )

    toc_items = "\n".join(
        f'<button type="button" class="toc-item" data-index="{i}" '
        f'data-n="{c["n"]}">{escape(c["title"])}</button>'
        for i, c in enumerate(chapters)
    )

    chapter_options = "\n".join(
        f'<option value="{c["n"]}">{escape(c["title"])}</option>' for c in chapters
    )
    first_n = chapters[0]["n"] if chapters else 1
    last_n = chapters[-1]["n"] if chapters else 1

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(story_title)} — Local Reader</title>
  <style>
    :root {{
      --bg: #f7f4ef;
      --panel: #fffdf9;
      --ink: #1c1917;
      --muted: #78716c;
      --accent: #0f766e;
      --accent-soft: #ccfbf1;
      --border: #e7e5e4;
      --serif: "Literata", "Source Serif 4", "Noto Serif", Georgia, serif;
      --sans: "Be Vietnam Pro", "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(1200px 600px at 10% -10%, #dbeafe 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #fde68a55 0%, transparent 50%),
        var(--bg);
      min-height: 100vh;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 100vh;
    }}
    .sidebar {{
      background: var(--panel);
      border-right: 1px solid var(--border);
      padding: 1.25rem 1rem;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
    }}
    .sidebar h1 {{
      font-size: 1.05rem;
      margin: 0 0 0.35rem;
      line-height: 1.35;
      font-family: var(--serif);
    }}
    .sidebar .meta {{
      color: var(--muted);
      font-size: 0.8rem;
      margin-bottom: 0.85rem;
    }}
    .range-box {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem;
      margin-bottom: 1rem;
      background: #fafaf9;
    }}
    .range-box .label {{
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 0.55rem;
    }}
    .range-row {{
      display: grid;
      gap: 0.4rem;
      margin-bottom: 0.55rem;
    }}
    .range-row label {{
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .range-row select {{
      width: 100%;
      font: inherit;
      font-size: 0.85rem;
      padding: 0.45rem 0.5rem;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: white;
      color: var(--ink);
    }}
    .range-box .actions {{
      display: flex;
      gap: 0.4rem;
      margin-top: 0.35rem;
    }}
    .range-box button {{
      flex: 1;
      border: 1px solid var(--border);
      background: var(--accent);
      color: white;
      border-radius: 8px;
      padding: 0.5rem 0.6rem;
      cursor: pointer;
      font: inherit;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .range-box button.secondary {{
      background: var(--panel);
      color: var(--ink);
    }}
    .range-box button:hover {{ filter: brightness(0.96); }}
    .toc {{
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }}
    .toc-item {{
      text-align: left;
      border: none;
      background: transparent;
      padding: 0.55rem 0.65rem;
      border-radius: 8px;
      cursor: pointer;
      font: inherit;
      font-size: 0.88rem;
      color: var(--ink);
      line-height: 1.35;
    }}
    .toc-item:hover {{ background: #f5f5f4; }}
    .toc-item.active {{
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
    }}
    .main {{
      padding: 1.5rem 1.75rem 3rem;
      max-width: 48rem;
      width: 100%;
      margin: 0 auto;
    }}
    .toolbar {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 1.25rem;
      position: sticky;
      top: 0;
      background: color-mix(in srgb, var(--bg) 88%, white);
      backdrop-filter: blur(8px);
      padding: 0.65rem 0;
      z-index: 2;
    }}
    .toolbar button {{
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--ink);
      border-radius: 8px;
      padding: 0.5rem 0.9rem;
      cursor: pointer;
      font: inherit;
      font-size: 0.9rem;
    }}
    .toolbar button:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}
    .toolbar button:not(:disabled):hover {{
      border-color: var(--accent);
      color: var(--accent);
    }}
    .range-summary {{
      color: var(--muted);
      font-size: 0.88rem;
      margin-left: 0.25rem;
    }}
    .chapter-block {{
      margin-bottom: 2.75rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--border);
    }}
    .chapter-block:last-child {{
      border-bottom: none;
      margin-bottom: 0;
      padding-bottom: 0;
    }}
    .chapter-heading {{
      font-family: var(--serif);
      font-size: clamp(1.35rem, 2.5vw, 1.75rem);
      margin: 0 0 1rem;
      line-height: 1.3;
      color: var(--accent);
    }}
    .chapter-body {{
      font-family: var(--serif);
      font-size: 1.12rem;
      line-height: 1.85;
    }}
    .chapter-body p {{ margin: 0 0 0.95em; }}
    .chapter-body br + br {{ display: block; margin-top: 0.6em; content: ""; }}
    .menu-toggle {{
      display: none;
      margin-bottom: 0.75rem;
    }}
    @media (max-width: 860px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{
        position: fixed;
        inset: 0 auto 0 0;
        width: min(86vw, 300px);
        transform: translateX(-105%);
        transition: transform 0.2s ease;
        z-index: 10;
        box-shadow: 8px 0 30px #0002;
      }}
      .sidebar.open {{ transform: translateX(0); }}
      .menu-toggle {{ display: inline-block; }}
      .main {{ padding: 1rem 1rem 2.5rem; }}
    }}
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600&family=Literata:opsz,wght@7..72,400;7..72,600&display=swap" rel="stylesheet">
</head>
<body>
  <div class="layout">
    <aside class="sidebar" id="sidebar">
      <h1>{escape(story_title)}</h1>
      <div class="meta">{len(chapters)} chương · đọc offline</div>
      <div class="range-box">
        <div class="label">Chọn khoảng chương</div>
        <div class="range-row">
          <label for="fromSelect">Từ chương</label>
          <select id="fromSelect">{chapter_options}
          </select>
        </div>
        <div class="range-row">
          <label for="toSelect">Đến chương</label>
          <select id="toSelect">{chapter_options}
          </select>
        </div>
        <div class="actions">
          <button type="button" id="loadRangeBtn">Xem khoảng</button>
          <button type="button" class="secondary" id="resetRangeBtn">1 chương</button>
        </div>
      </div>
      <nav class="toc" id="toc">{toc_items}
      </nav>
    </aside>
    <main class="main">
      <button type="button" class="menu-toggle toolbar" id="menuBtn" style="border:1px solid var(--border);background:var(--panel);border-radius:8px;padding:0.5rem 0.9rem;cursor:pointer;font:inherit;">Mục lục</button>
      <div class="toolbar">
        <button type="button" id="prevBtn">← Trước</button>
        <button type="button" id="nextBtn">Sau →</button>
        <span class="range-summary" id="rangeSummary"></span>
      </div>
      <div id="reader"></div>
    </main>
  </div>
  <script>
    const CHAPTERS = {chapters_json};
    const byN = Object.fromEntries(CHAPTERS.map(c => [c.n, c]));
    let rangeFrom = {first_n};
    let rangeTo = {first_n};
    const reader = document.getElementById('reader');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const toc = document.getElementById('toc');
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('menuBtn');
    const fromSelect = document.getElementById('fromSelect');
    const toSelect = document.getElementById('toSelect');
    const loadRangeBtn = document.getElementById('loadRangeBtn');
    const resetRangeBtn = document.getElementById('resetRangeBtn');
    const rangeSummary = document.getElementById('rangeSummary');

    function clampPair(a, b) {{
      let from = Math.min(a, b);
      let to = Math.max(a, b);
      if (!(from in byN)) from = CHAPTERS[0].n;
      if (!(to in byN)) to = CHAPTERS[CHAPTERS.length - 1].n;
      return [from, to];
    }}

    function showRange(fromN, toN) {{
      [rangeFrom, rangeTo] = clampPair(Number(fromN), Number(toN));
      fromSelect.value = String(rangeFrom);
      toSelect.value = String(rangeTo);

      const selected = CHAPTERS.filter(c => c.n >= rangeFrom && c.n <= rangeTo);
      reader.innerHTML = selected.map(ch => `
        <section class="chapter-block" id="chuong-${{ch.n}}">
          <h2 class="chapter-heading">${{ch.title}}</h2>
          <article class="chapter-body">${{ch.content_html}}</article>
        </section>
      `).join('');

      const count = selected.length;
      rangeSummary.textContent = count === 1
        ? selected[0].title
        : `Chương ${{rangeFrom}} → ${{rangeTo}} (${{count}} chương)`;

      toc.querySelectorAll('.toc-item').forEach(el => {{
        const n = Number(el.dataset.n);
        el.classList.toggle('active', n >= rangeFrom && n <= rangeTo);
      }});

      const firstIdx = CHAPTERS.findIndex(c => c.n === rangeFrom);
      const lastIdx = CHAPTERS.findIndex(c => c.n === rangeTo);
      prevBtn.disabled = firstIdx <= 0;
      nextBtn.disabled = lastIdx >= CHAPTERS.length - 1;

      const hash = rangeFrom === rangeTo
        ? '#chuong-' + rangeFrom
        : '#chuong-' + rangeFrom + '-' + rangeTo;
      history.replaceState(null, '', hash);
      window.scrollTo({{ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' }});
    }}

    function showOne(n) {{
      showRange(n, n);
    }}

    loadRangeBtn.addEventListener('click', () => {{
      showRange(fromSelect.value, toSelect.value);
      sidebar.classList.remove('open');
    }});
    resetRangeBtn.addEventListener('click', () => {{
      showOne(Number(fromSelect.value));
      sidebar.classList.remove('open');
    }});
    fromSelect.addEventListener('change', () => {{
      if (Number(fromSelect.value) > Number(toSelect.value)) {{
        toSelect.value = fromSelect.value;
      }}
    }});
    toSelect.addEventListener('change', () => {{
      if (Number(toSelect.value) < Number(fromSelect.value)) {{
        fromSelect.value = toSelect.value;
      }}
    }});

    toc.addEventListener('click', (e) => {{
      const btn = e.target.closest('.toc-item');
      if (!btn) return;
      showOne(Number(btn.dataset.n));
      sidebar.classList.remove('open');
    }});

    prevBtn.addEventListener('click', () => {{
      const firstIdx = CHAPTERS.findIndex(c => c.n === rangeFrom);
      if (firstIdx <= 0) return;
      const span = rangeTo - rangeFrom;
      const newFrom = CHAPTERS[Math.max(0, firstIdx - 1 - span)].n;
      const newTo = CHAPTERS[firstIdx - 1].n;
      showRange(newFrom, newTo);
    }});
    nextBtn.addEventListener('click', () => {{
      const lastIdx = CHAPTERS.findIndex(c => c.n === rangeTo);
      if (lastIdx >= CHAPTERS.length - 1) return;
      const span = rangeTo - rangeFrom;
      const newFrom = CHAPTERS[lastIdx + 1].n;
      const newTo = CHAPTERS[Math.min(CHAPTERS.length - 1, lastIdx + 1 + span)].n;
      showRange(newFrom, newTo);
    }});
    menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));

    const rangeHash = location.hash.match(/chuong-(\\d+)-(\\d+)/);
    const singleHash = location.hash.match(/chuong-(\\d+)/);
    if (rangeHash) {{
      showRange(rangeHash[1], rangeHash[2]);
    }} else if (singleHash) {{
      showOne(Number(singleHash[1]));
    }} else {{
      showOne({first_n});
    }}
  </script>
</body>
</html>
"""


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
    meta = serialize_chapters(chapters)
    for m, ch in zip(meta, chapters):
        ch["path"] = m["path"]
        ch["text"] = read_chapter_text(m["path"])
    (OUT_DIR / "chapters.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    title = story_title or (
        chapters[0].get("story") if chapters else "Đại Vương Tha Mạng"
    )
    (OUT_DIR / "index.html").write_text(
        build_index_html(chapters, title or "Đại Vương Tha Mạng"),
        encoding="utf-8",
    )


def regenerate_index() -> None:
    by_n = load_existing_chapters()
    chapters = [by_n[k] for k in sorted(by_n)]
    if not chapters:
        raise SystemExit("No chapters to build")
    story = chapters[0].get("story") or "Đại Vương Tha Mạng"
    (OUT_DIR / "index.html").write_text(
        build_index_html(chapters, story), encoding="utf-8"
    )
    print(f"Regenerated index.html with {len(chapters)} chapter(s)")


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
    args = parser.parse_args()

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

    for i, n in enumerate(range(args.start, args.end + 1), start=1):
        print(f"[{i}/{total}] Fetching chapter {n} (delay={args.delay}s)...")
        ch = fetch_chapter(n, session)
        by_n[n] = ch
        story_title = ch["story"]
        print(f"  OK: {ch['title']} ({len(ch['text'])} chars)")
        if n < args.end:
            print(f"  waiting {args.delay}s...")
            time.sleep(args.delay)

    chapters = [by_n[k] for k in sorted(by_n)]
    if chapters:
        story_title = chapters[0].get("story") or story_title

    save_library(chapters, story_title)

    print(f"\nWrote {OUT_DIR / 'index.html'}")
    print(f"Wrote {OUT_DIR / 'chapters.json'}")
    print(f"Wrote chapter text under {CHAPTERS_DIR}/")
    print(f"Crawled: {args.start}–{args.end}; library now has {len(chapters)} chapter(s)")


if __name__ == "__main__":
    main()
