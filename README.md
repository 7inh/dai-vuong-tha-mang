# Đại Vương Tha Mạng — Next.js reader

Vietnamese novel reader built with Next.js. Chapter text lives in `chapters/*.txt`; metadata in `chapters.json`. Chapter pages are statically generated at build time for fast loading and Safari Reader support.

## Local preview

```bash
npm install
npm run dev        # http://localhost:3000 (first page load may take ~20s)
```

- Single chapter: `/chuong/1`
- Range reading: `/doc?from=1&to=5`
- Safari Reader: open any `/chuong/N` page — content is server-rendered semantic HTML

Production build:

```bash
npm run build      # generates ~1331 static /chuong/[n] pages
npm run start
```

## Crawl more chapters

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-crawl.txt

python crawl.py --start 300 --end 1334 --delay 2
# Resume-safe: skips chapters that already exist on disk

# After a long crawl (or if json lags behind txt files):
python crawl.py --sync
```

## Deploy to Vercel

Live: **https://dai-vuong-tha-mang.vercel.app**

Next.js app — Vercel runs `next build` on every push to `main`.

### Sync → GitHub → Vercel

```bash
python crawl.py --sync
git add chapters chapters.json
git commit -m "Add crawled chapters"
git push origin main   # triggers Vercel production deploy
```

### CLI (optional)

```bash
npx vercel link --project dai-vuong-tha-mang   # once
npx vercel --prod                              # manual deploy
```

## Project layout

| Path | Role |
|------|------|
| `app/` | Next.js App Router pages and layout |
| `components/` | Reader UI (Sidebar, ChapterNav, ChapterBody) |
| `lib/chapters.ts` | Read `chapters.json` + txt files from disk |
| `chapters.json` | Metadata: `n`, `title`, `path`, … |
| `chapters/chuong-N.txt` | Chapter bodies |
| `crawl.py` | Fetches chapters from the source site |
| `requirements-crawl.txt` | Python deps for the crawler (not used by Vercel) |
| `.vercelignore` | Keeps crawl tooling out of deployments |
