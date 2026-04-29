from notion_client import Client
from config import NOTION_TOKEN, ARTICLE_DB_ID, IDEA_DB_ID

notion = Client(auth=NOTION_TOKEN)

print("建立文章 DB 欄位...")
notion.databases.update(
    ARTICLE_DB_ID,
    properties={
        "URL":    {"url": {}},
        "分類":   {"multi_select": {}},
        "存入日期": {"date": {}},
        "已讀":   {"checkbox": {}},
    },
)
print("文章 DB OK")

print("建立想法 DB 欄位...")
notion.databases.update(
    IDEA_DB_ID,
    properties={
        "分類": {"multi_select": {}},
        "日期": {"date": {}},
    },
)
print("想法 DB OK")
