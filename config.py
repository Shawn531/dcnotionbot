import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ARTICLE_DB_ID = os.environ["NOTION_ARTICLE_DB_ID"]
IDEA_DB_ID = os.environ["NOTION_IDEA_DB_ID"]
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")
