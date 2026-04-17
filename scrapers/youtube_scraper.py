import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from duckduckgo_search import DDGS
from core.utils import get_random_user_agent, EMAIL_REGEX, is_valid_match

class YouTubeScraper:
    async def find_channel_and_email(self, business_name: str, location: str) -> Optional[str]:
        """Find YouTube channel and extract email from description."""
        query = f'"{business_name}" "{location}" youtube channel'
        channel_url = None
        
        try:
            # 1. Find Channel URL via DDG
            with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                results = list(ddgs.text(query, max_results=3))
                for r in results:
                    if "youtube.com/channel/" in r['href'] or "youtube.com/@" in r['href']:
                        channel_url = r['href']
                        break
        except:
            pass
            
        if not channel_url:
            return None
            
        # 2. Visit Channel with Playwright
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=get_random_user_agent())
                await Stealth().apply_stealth_async(page)
                
                # Visit 'About' or main page for description
                await page.goto(channel_url, wait_until="networkidle", timeout=30000)
                
                # Extract text from the whole page (About section is often inline now in new UI)
                content = await page.content()
                emails = re.findall(EMAIL_REGEX, content)
                
                if emails:
                    return emails[0].lower()
                    
            except Exception as e:
                # print(f"YouTubeScraper error: {e}")
                pass
            finally:
                await browser.close()
                
        return None
