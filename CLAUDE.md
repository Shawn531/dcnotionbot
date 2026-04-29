# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running Locally (persistent bot mode)

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Architecture

Two modes: **persistent bot** (`main.py`) and **batch** (`batch_process.py`). Production uses batch mode via GitHub Actions.

### Routing (tag-priority)

The first `#tag` determines the destination:
- `#想法` → Ideas database (ignores URL)
- Any other tag or no tag (when URL present) → Articles database
- No tags + no URL → ignored

### Module responsibilities

- `config.py` — loads `.env`, exports `DISCORD_TOKEN`, `NOTION_TOKEN`, `ARTICLE_DB_ID`, `IDEA_DB_ID`
- `scraper.py` — `async get_page_info(url) → (title, content, images)`. Threads/FB URLs use Playwright + `threads_cookies.json`; others use httpx + BeautifulSoup. Image extraction targets CDN images ≥200px.
- `notion_helper.py` — `create_article_page()` and `create_idea_page()`; splits content into 2000-char paragraph blocks; returns page URL
- `main.py` — persistent Discord WebSocket bot (local dev / fallback)
- `batch_process.py` — reads last 50 messages from a Discord channel via REST API, processes those without a ✅ bot reaction, saves to Notion, then adds ✅ reaction

### Content extraction (scraper.py)

- `_extract_thread_posts(body, author)`: walks `document.body.innerText`, collects author's posts (separated by `---`), stops at comment section (detects non-author username + timestamp pattern)
- `_extract_facebook_post(body)`: uses `的貼文` as start marker, `所有心情：` as stop
- Both truncate at 8000 chars

## Batch Deployment (GitHub Actions + cron-job.org)

**Workflow:** `.github/workflows/process_discord.yml` — triggered by `workflow_dispatch` (called by cron-job.org) or daily schedule.

**GitHub Secrets required:**

| Secret | Description |
|---|---|
| `DISCORD_TOKEN` | Bot token |
| `DISCORD_CHANNEL_ID` | Channel ID to poll |
| `NOTION_TOKEN` | Notion integration token |
| `NOTION_ARTICLE_DB_ID` | Articles database ID |
| `NOTION_IDEA_DB_ID` | Ideas database ID |
| `THREADS_COOKIES` | Full contents of `threads_cookies.json` |

**Setting up cron-job.org:**
1. Create a job with URL: `https://api.github.com/repos/{owner}/{repo}/actions/workflows/process_discord.yml/dispatches`
2. Method: POST
3. Headers: `Authorization: Bearer {github_pat}`, `Accept: application/vnd.github+json`
4. Body: `{"ref":"main"}`
5. GitHub PAT needs `repo` or `actions:write` scope

## Notion Database Fields

**Articles DB**: Name (Title), URL, 分類 (Multi-select), 存入日期 (Date), 已讀 (Checkbox)

**Ideas DB**: Name (Title ≤30 chars), 分類 (Multi-select), 日期 (Date); full text in page body

## Cookie Refresh

When Threads/FB login expires, re-run locally:
```bash
python scripts/save_cookies.py
```
Then update the `THREADS_COOKIES` GitHub Secret with the new `threads_cookies.json` contents.
