import re
from datetime import datetime, timezone
import discord
from config import DISCORD_TOKEN
from scraper import get_page_info
from notion_helper import create_article_page, create_idea_page

TAG_RE = re.compile(r"#(\S+)")
URL_RE = re.compile(r"https?://\S+")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

_processed: set[int] = set()


def _extract_title_from_text(text: str) -> str:
    first = re.split(r"[。\n]", text)[0].strip()
    return first[:30] if len(first) > 30 else first


@client.event
async def on_ready():
    print(f"Bot online as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Ignore replayed/old messages (Discord session resume replays recent events)
    age = (datetime.now(timezone.utc) - message.created_at).total_seconds()
    if age > 60:
        return
    if message.id in _processed:
        return
    _processed.add(message.id)

    tags = TAG_RE.findall(message.content)
    all_tags = list(dict.fromkeys(tags))
    first_tag = tags[0] if tags else None

    if first_tag == "想法":
        content = TAG_RE.sub("", message.content).strip()
        title = _extract_title_from_text(content)
        other_tags = [t for t in all_tags if t != "想法"]
        notion_url = create_idea_page(title, content, other_tags)
        await message.reply(f"✅ 想法已存入 Notion\n{notion_url}")
    else:
        urls = URL_RE.findall(message.content)
        if not urls:
            return
        url = urls[0]
        title, content, images = await get_page_info(url)
        notion_url = create_article_page(title, url, all_tags, content, images)
        await message.reply(f"✅ 文章已存入 Notion\n{notion_url}")


client.run(DISCORD_TOKEN)
