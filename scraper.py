import json
import os
import re
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

_SOCIAL_DOMAINS = ("threads.net", "threads.com", "facebook.com", "fb.com", "fb.watch")
_COOKIE_FILE = os.path.join(os.path.dirname(__file__), "threads_cookies.json")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


async def get_page_info(url: str) -> tuple[str, str, list[str]]:
    """Return (title, content, image_urls)."""
    if any(d in url for d in _SOCIAL_DOMAINS):
        return await _get_with_browser(url)
    title, content = await _get_with_httpx(url)
    return title, content, []


def _load_cookies() -> list[dict]:
    if os.path.exists(_COOKIE_FILE):
        with open(_COOKIE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


async def _get_with_browser(url: str) -> tuple[str, str]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(extra_http_headers={"Accept-Language": "zh-TW,zh;q=0.9"})
            cookies = _load_cookies()
            if cookies:
                await context.add_cookies(cookies)
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            title = await page.evaluate(
                "() => document.querySelector('meta[property=\"og:title\"]')?.content"
                "     || document.title || ''"
            )

            body_text = await page.evaluate("() => document.body.innerText")
            if any(d in url for d in ("facebook.com", "fb.com", "fb.watch")):
                content = _extract_facebook_post(body_text)
            else:
                author = _author_from_url(url)
                content = _extract_thread_posts(body_text, author)

            images = await page.evaluate("""() => {
                const seen = new Set();
                return Array.from(document.querySelectorAll('img'))
                    .filter(img => {
                        const src = img.src || '';
                        const w = img.naturalWidth || img.width || 0;
                        const h = img.naturalHeight || img.height || 0;
                        return w >= 200 && h >= 200
                            && !seen.has(src) && seen.add(src)
                            && (src.includes('cdninstagram') || src.includes('fbcdn')
                                || src.includes('threads'));
                    })
                    .map(img => img.src);
            }""")

            await context.close()
            await browser.close()
            return (title or url).strip(), content.strip(), images
    except Exception:
        return url, "", []


async def _get_with_httpx(url: str) -> tuple[str, str]:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")

        og_title = soup.find("meta", {"property": "og:title"})
        title_tag = soup.find("title")
        title = (
            (og_title.get("content", "").strip() if og_title else "")
            or (title_tag.string.strip() if title_tag and title_tag.string else "")
            or url
        )

        content = _article_text(soup) or _og_description(soup)
        return title, content
    except Exception:
        return url, ""


def _author_from_url(url: str) -> str:
    """Extract username from threads URL, e.g. '@u_sandrin3' → 'u_sandrin3'."""
    m = re.search(r"/@([^/?]+)", url)
    return m.group(1) if m else ""


def _extract_thread_posts(body: str, author: str) -> str:
    """
    Parse Threads page body text and return only the author's post content,
    concatenating all parts of a multi-post thread.
    """
    if not author:
        return body[:8000]

    lines = body.splitlines()
    _UI = {
        "For you", "New thread", "Search", "Activity", "Profile",
        "Insights", "Saved", "Feeds", "Edit", "Following",
        "Ghost posts", "More", "Thread", "Top", "View activity", "Translate",
        "熱門", "查看動態", "/", "·", "作者", "Author",
    }
    _PAGINATION = re.compile(r"^(\d+\s*/\s*\d+|\d+)$")
    _TIMESTAMP = re.compile(r"^\d+\s*(秒|分鐘|小時|天|週|個月|年)(前)?$|^剛剛$|^\d+[smhdw]$")
    _USERNAME  = re.compile(r"^[a-zA-Z0-9._]+$")

    posts: list[str] = []
    collecting = False
    current: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Author line → next meaningful line is timestamp, then content starts
        if line == author:
            # save previous collected block
            if current:
                posts.append("\n".join(current).strip())
                current = []
            collecting = True
            i += 2  # skip author + timestamp line
            continue

        if collecting:
            if line in _UI or _PAGINATION.match(line) or _TIMESTAMP.match(line):
                i += 1
                continue
            # Detect comments section: non-author username followed by a timestamp
            if _USERNAME.match(line) and line != author:
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if _TIMESTAMP.match(next_line):
                    if current:
                        posts.append("\n".join(current).strip())
                        current = []
                    collecting = False
                    break
            current.append(line)

        i += 1

    if current:
        posts.append("\n".join(current).strip())

    result = "\n\n---\n\n".join(p for p in posts if p)
    return result[:8000]


def _extract_facebook_post(body: str) -> str:
    """Extract post content from Facebook page body text."""
    _STOP = {"所有心情：", "讚", "留言", "分享", "最相關", "最新", "所有留言"}
    _SKIP = {"登入", "忘記帳號？", "建立新帳號", "·", " ", "加入", "追蹤", "或", "忘記密碼？"}

    lines = body.splitlines()
    collecting = False
    result: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Start marker 1: page post ("X 的貼文")
        if not collecting and line.endswith("的貼文"):
            _SKIP.add(line[:-3].strip())
            collecting = True
            continue

        # Start marker 2: group post — first date timestamp (e.g. "4月15日下午12:41")
        if not collecting and _TIMESTAMP_FB_POST.match(line):
            collecting = True
            continue

        if not collecting:
            continue

        if line in _SKIP:
            continue

        if line in _STOP or line.startswith("所有心情"):
            break

        if _TIMESTAMP_FB.match(line) or _TIMESTAMP_FB_POST.match(line):
            continue

        result.append(line)

    return "\n".join(result).strip()[:8000]


_TIMESTAMP_FB = re.compile(
    r"^\d+\s*(秒|分鐘|小時|天|週|個月|年)(前)?$|^剛剛$|^\d+[smhdw]$"
)

# Group post timestamp: "4月15日下午12:41", "昨天上午9:00", "今天", etc.
_TIMESTAMP_FB_POST = re.compile(
    r"^\d+月\d+日|^昨天[上下]午|^今天[上下]午"
)


def _og_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", {"property": "og:description"})
    return tag["content"].strip() if tag and tag.get("content") else ""


def _article_text(soup: BeautifulSoup) -> str:
    container = soup.find("article") or soup.find("main")
    if not container:
        return ""
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    text = "\n\n".join(p for p in paragraphs if len(p) > 40)
    return text[:8000]
