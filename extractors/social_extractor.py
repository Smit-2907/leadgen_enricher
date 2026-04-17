"""
Social Bio Extractor — scrapes Instagram/Facebook/etc. bios for emails.
Uses Playwright with stealth since socials block curl.
"""
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from search.utils import random_ua, extract_emails

PLATFORM_CONFIGS = {
    "instagram": {
        "wait": "domcontentloaded",
        "scroll": True,
        "timeout": 20000,
    },
    "facebook": {
        "wait": "domcontentloaded",
        "scroll": False,
        "timeout": 20000,
    },
    "default": {
        "wait": "domcontentloaded",
        "scroll": False,
        "timeout": 15000,
    },
}


async def scrape_social_bio(url: str, platform: str = "default") -> Optional[str]:
    """
    Visit a social profile page and extract any email from the bio/about section.
    Returns first valid email found, or None.
    """
    if not url or "explore/tags" in url or "/reel/" in url or "/p/" in url:
        return None

    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["default"])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(user_agent=random_ua())
            page = await ctx.new_page()
            await Stealth().apply_stealth_async(page)
            await page.goto(url, wait_until=config["wait"], timeout=config["timeout"])
            await asyncio.sleep(2)

            if config["scroll"]:
                await page.evaluate("window.scrollTo(0, 300)")
                await asyncio.sleep(1)

            content = await page.content()
            emails = extract_emails(content)
            return emails[0] if emails else None
        except Exception:
            return None
        finally:
            await browser.close()
