import asyncio
import json
import os
import re

import httpx

from notion_helper import create_article_page, create_idea_page
from scraper import get_page_info

TAG_RE = re.compile(r"#(\S+)")
URL_RE = re.compile(r"https?://\S+")

DISCORD_API = "https://discord.com/api/v10"
CHANNEL_ID = os.environ["DISCORD_CHANNEL_ID"]
_BOT_HEADERS = {"Authorization": f"Bot {os.environ['DISCORD_TOKEN']}"}

# URL-encoded ✅
_CHECK_EMOJI = "%E2%9C%85"


def _is_processed(msg: dict) -> bool:
    for r in msg.get("reactions", []):
        if r.get("emoji", {}).get("name") == "✅" and r.get("me"):
            return True
    return False


def _extract_title(text: str) -> str:
    first = re.split(r"[。\n]", text)[0].strip()
    return first[:30]


async def _fetch_messages(client: httpx.AsyncClient, limit: int = 50) -> list[dict]:
    resp = await client.get(
        f"{DISCORD_API}/channels/{CHANNEL_ID}/messages",
        params={"limit": limit},
    )
    resp.raise_for_status()
    return resp.json()


async def _add_reaction(client: httpx.AsyncClient, message_id: str) -> None:
    await client.put(
        f"{DISCORD_API}/channels/{CHANNEL_ID}/messages/{message_id}/reactions/{_CHECK_EMOJI}/@me"
    )


async def _send_reply(client: httpx.AsyncClient, message_id: str, text: str) -> None:
    await client.post(
        f"{DISCORD_API}/channels/{CHANNEL_ID}/messages",
        json={"content": text, "message_reference": {"message_id": message_id}},
    )


async def _process(client: httpx.AsyncClient, msg: dict) -> bool:
    content = msg["content"]
    tags = TAG_RE.findall(content)
    all_tags = list(dict.fromkeys(tags))
    first_tag = tags[0] if tags else None

    if first_tag == "想法":
        text = TAG_RE.sub("", content).strip()
        title = _extract_title(text)
        other_tags = [t for t in all_tags if t != "想法"]
        notion_url = create_idea_page(title, text, other_tags)
        await _send_reply(client, msg["id"], f"✅ 想法已存入 Notion\n{notion_url}")
        return True

    urls = URL_RE.findall(content)
    if not urls:
        return False

    url = urls[0]
    title, article_content, images = await get_page_info(url)
    print(f"[debug] url={url} title={title!r} content_len={len(article_content)} images={len(images)}")
    notion_url = create_article_page(title, url, all_tags, article_content, images)
    await _send_reply(client, msg["id"], f"✅ 文章已存入 Notion\n{notion_url}")
    return True


async def main() -> None:
    # Write cookies from GitHub Secret to file so scraper can load them
    cookies_json = os.environ.get("THREADS_COOKIES")
    if cookies_json:
        cookies_path = os.path.join(os.path.dirname(__file__), "threads_cookies.json")
        with open(cookies_path, "w", encoding="utf-8") as f:
            f.write(cookies_json)

    async with httpx.AsyncClient(headers=_BOT_HEADERS, timeout=30) as client:
        messages = await _fetch_messages(client)

        for msg in reversed(messages):  # oldest first
            if msg["author"].get("bot"):
                continue
            if _is_processed(msg):
                print(f"Skipping already processed message {msg['id']}")
                continue

            try:
                processed = await _process(client, msg)
                if processed:
                    await _add_reaction(client, msg["id"])
                    print(f"Processed message {msg['id']}")
            except Exception as e:
                print(f"Error on message {msg['id']}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
