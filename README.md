# Đại Vương Tha Mạng — offline / Vercel reader

Static Vietnamese novel reader. Chapter text lives in `chapters/*.txt`; the browser loads `chapters.json` then fetches chapters on demand.

## Local preview

Serve the project root (required so `fetch()` works — do not open `index.html` as a `file://` URL):

```bash
cd dai-vuong-tha-mang-reader
python3 -m http.server 8080
# open http://localhost:8080
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

Static site — no build step. Tracked in GitHub [`7inh/dai-vuong-tha-mang`](https://github.com/7inh/dai-vuong-tha-mang); Vercel project `dai-vuong-tha-mang` deploys on every push to `main`.

### Sync → GitHub → Vercel

```bash
# after crawling more chapters
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
| `index.html` | Lazy-load reader UI (committed, not overwritten by crawl) |
| `chapters.json` | Metadata: `n`, `title`, `path`, … |
| `chapters/chuong-N.txt` | Chapter bodies |
| `crawl.py` | Fetches chapters from the source site |
| `requirements-crawl.txt` | Python deps for the crawler (not used by Vercel) |
| `vercel.json` | Static site + cache / charset headers |
| `.vercelignore` | Keeps crawl tooling out of deployments |
