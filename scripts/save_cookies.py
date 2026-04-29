import asyncio
import json
from playwright.async_api import async_playwright

COOKIE_FILE = "threads_cookies.json"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.threads.com/login")
        print("請在瀏覽器視窗登入 Threads，登入完成後回到這裡按 Enter...")
        input()

        await page.goto("https://www.facebook.com/login")
        print("請在瀏覽器視窗登入 Facebook，登入完成後回到這裡按 Enter...")
        input()

        cookies = await context.cookies()
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f)

        await browser.close()
        domains = set(c.get("domain", "") for c in cookies)
        print(f"Cookie 已儲存到 {COOKIE_FILE}（共 {len(cookies)} 筆，網域：{domains}）")

asyncio.run(main())
