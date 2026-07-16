# praviveek.online — Notes

Static blog on GitHub Pages. A bot posts an AI/tech digest every weekday, arXiv
paper picks alongside it, and a synthesis roundup on Fridays. You add your own
writing and research as markdown files.

---

## 1. Create the repo

1. GitHub → **New repository** → name it **`praviveek.online`** → **Public** → Create.
2. **Add file → Upload files** → drag in *everything* from this folder, keeping the
   structure (`data/`, `posts/`, `scripts/`, `.github/workflows/`) → Commit.
   - If drag-and-drop flattens the folders, upload folder by folder.
3. **Settings → Pages** → Source: **Deploy from a branch** → `main` / `/ (root)` → Save.

Live at `https://21pravi.github.io/praviveek.online/` within a minute.

## 2. Point the domain (Hostinger)

Same pattern as praviveek.com.

1. Hostinger → **Domains → praviveek.online → DNS records**.
2. Delete the existing `@` **A** record (the parking IP).
3. Add four **A** records, name `@`:
   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```
4. Add a **CNAME**: name `www` → value `21pravi.github.io`
5. GitHub → **Settings → Pages → Custom domain** → `praviveek.online` → Save.
   (A `CNAME` file is already included, so this should populate itself.)
6. Once the DNS check goes green, tick **Enforce HTTPS**.

## 3. Add your API key (required for the bot)

The bot uses Gemini to write summaries. Get a key at **aistudio.google.com/apikey**.

GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `GEMINI_API_KEY`
- Value: your key

Then **Settings → Actions → General → Workflow permissions** → select
**Read and write permissions** → Save. (The bot needs this to commit its posts.)

**Model:** `gemini-3.1-flash-lite` (Google's high-volume, low-cost workhorse). The
free tier's rate limits comfortably cover ~6 calls a week, so this should cost you
nothing. To use a smarter model, set a `GEMINI_MODEL` repo variable to
`gemini-3.5-flash` — or edit `MODEL` in `scripts/llm.py`.

> Note: `gemini-2.0-flash` was shut down on 2026-06-01. Don't use it.

## 4. Turn on comments (Giscus)

1. Repo → **Settings → General → Features** → tick **Discussions**.
2. Install the Giscus app: **github.com/apps/giscus** → grant it access to this repo.
3. Go to **giscus.app**, enter `21pravi/praviveek.online`, pick the
   **Announcements** category. It will show you a `data-repo-id` and `data-category-id`.
4. Open `post.html`, find the Giscus block near the bottom, and replace:
   - `YOUR_REPO_ID` → the repo ID it gave you
   - `YOUR_CATEGORY_ID` → the category ID it gave you

## 5. Turn on the newsletter (Buttondown)

1. Sign up at **buttondown.com** (free up to 100 subscribers).
2. Open `index.html`, find `YOUR_USERNAME` in the subscribe form, replace it with
   your Buttondown username.

Prefer a different provider? Swap the form's `action` URL for theirs — the markup
is standard.

## 6. Test the bot before waiting for the cron

Repo → **Actions** tab → **Daily digest** → **Run workflow**.
Watch it run; in ~1 minute `data/news.json` gets a new commit and the site updates.

---

## Writing a post

Add a file to `posts/` named `your-slug.md`:

```markdown
---
title: What churn models actually miss
date: 2026-07-20
type: writing
tags: [churn, telecom, ml]
excerpt: One sentence that shows up on the homepage card.
---

Your content here. Standard markdown — headings, **bold**, `code`,
lists, > quotes, tables, images.
```

Front-matter fields:

| Field | Required | Notes |
|---|---|---|
| `title` | yes | Post title |
| `date` | yes | `YYYY-MM-DD`, controls ordering |
| `type` | no | `writing` (default) or `research` — changes the badge |
| `tags` | no | `[tag1, tag2]` |
| `excerpt` | no | Homepage teaser; auto-generated if omitted |
| `pdf` | no | URL to a PDF — adds a download button |

Commit the file. The **Rebuild on new post** workflow regenerates `data/posts.json`
and the RSS feed automatically. Nothing else to touch.

### Posting research with a PDF

```markdown
---
title: Graph Convolutional Networks for Sentiment Classification
date: 2026-07-22
type: research
tags: [nlp, gcn]
pdf: https://drive.google.com/file/d/YOUR_FILE_ID/view
excerpt: 88.3% accuracy combining Word2Vec with TF-IDF embeddings.
---
```

---

## Tuning the bot

| What | Where |
|---|---|
| News sources | `FEEDS` in `scripts/fetch_news.py` |
| Stories per digest | `MAX_STORIES` (default 8) |
| Topic ranking | `BOOST` keyword list |
| Paper topics | `INTERESTS` in `scripts/fetch_papers.py` |
| Run times | `cron` lines in `.github/workflows/*.yml` (UTC — IST is UTC+5:30) |
| Gemini model | `MODEL` in `scripts/llm.py`, or the `GEMINI_MODEL` env var |

## How it stays legal

The digest publishes headlines, an **original** AI-written summary, and a link to
the source. It never reproduces article text. That's the difference between a
digest and a scraper — keep it that way if you edit the prompts.

## Files

```
index.html          Homepage — unified feed, filters, search, newsletter
post.html           Renders one markdown post + comments
CNAME               Custom domain for GitHub Pages
og-image.png        Social share banner
feed.xml            RSS (generated)
data/               Bot output + post index (generated)
posts/              Your markdown posts  ← you edit this
scripts/            The bots (llm.py = shared Gemini call)
.github/workflows/  Schedules
```
