import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from core.utils import get_random_user_agent, EMAIL_REGEX
import re

async def test_justdial():
    url = "https://www.justdial.com/Ahmedabad/Guli-Guli-Pet-Shop-Opposite-Jio-Tower-Vastrapur/079PXX79-XX79-240105151515-V8C7_BZDET"
    print(f"Testing JD Email Extraction for: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=get_random_user_agent())
        await Stealth().apply_stealth_async(page)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            content = await page.content()
            found = set(re.findall(EMAIL_REGEX, content))
            print(f"Emails strictly found on page content: {found}")
        except Exception as e:
            print(e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_justdial())