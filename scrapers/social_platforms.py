import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from core.utils import get_random_user_agent, EMAIL_REGEX

class SocialPlatformScraper:
    async def scrape_bio(self, url: str) -> Optional[str]:
        """Visit a social profile and extract text from the bio/about section."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=get_random_user_agent())
            await Stealth().apply_stealth_async(page)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Basic email extraction from full page text
                content = await page.content()
                emails = re.findall(EMAIL_REGEX, content)
                
                # Platform specific selectors could go here
                # For now, we use a generic approach to find any email in the bio
                if emails:
                    return emails[0]
                
            except Exception as e:
                print(f"SocialScraper error for {url}: {e}")
            finally:
                await browser.close()
        return None

    async def get_instagram_email(self, url: str) -> Optional[str]:
        # Instagram often hides info behind login, but sometimes public bios have it
        return await self.scrape_bio(url)

    async def get_facebook_email(self, url: str) -> Optional[str]:
        # FB pages often have an "About" section with emails
        if "/about" not in url:
            url = url.rstrip('/') + "/about"
        return await self.scrape_bio(url)
