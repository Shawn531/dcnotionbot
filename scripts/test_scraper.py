import asyncio
import sys
from scraper import get_page_info

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else input("貼上 URL: ").strip()
    title, content, images = await get_page_info(url)
    with open("scraper_output.txt", "w", encoding="utf-8") as f:
        f.write(f"[標題]\n{title}\n\n")
        f.write(f"[圖片] ({len(images)} 張)\n")
        for i, img in enumerate(images, 1):
            f.write(f"  {i}. {img[:100]}\n")
        f.write(f"\n[內文]\n{content}\n")
    print(f"完成：標題={title}，{len(images)} 張圖，內文 {len(content)} 字 → scraper_output.txt")

asyncio.run(main())
