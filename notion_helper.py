from datetime import datetime, timezone
from typing import Optional
from notion_client import Client
from config import NOTION_TOKEN, ARTICLE_DB_ID, IDEA_DB_ID

_notion = Client(auth=NOTION_TOKEN)

_CHUNK = 2000  # Notion rich_text block character limit


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _multi_select(tags: list[str]) -> list[dict]:
    return [{"name": t} for t in tags]


def _text_blocks(text: str) -> list[dict]:
    """Split long text into multiple paragraph blocks (2000-char limit each)."""
    blocks = []
    for i in range(0, max(len(text), 1), _CHUNK):
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text[i:i + _CHUNK]}}]
            },
        })
    return blocks


def _image_blocks(image_urls: list[str]) -> list[dict]:
    return [
        {"object": "block", "type": "image",
         "image": {"type": "external", "external": {"url": u}}}
        for u in image_urls
    ]


def create_article_page(title: str, url: str, tags: list[str],
                        content: str = "", images: Optional[list] = None) -> str:
    children = _text_blocks(content) if content else []
    if images:
        children += _image_blocks(images)
    resp = _notion.pages.create(
        parent={"database_id": ARTICLE_DB_ID},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "URL": {"url": url},
            "分類": {"multi_select": _multi_select(tags)},
            "存入日期": {"date": {"start": _now_iso()}},
            "已讀": {"checkbox": False},
        },
        children=children,
    )
    return resp["url"]


def create_idea_page(title: str, content: str, tags: list[str]) -> str:
    resp = _notion.pages.create(
        parent={"database_id": IDEA_DB_ID},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "分類": {"multi_select": _multi_select(tags)},
            "日期": {"date": {"start": _now_iso()}},
        },
        children=_text_blocks(content),
    )
    return resp["url"]
