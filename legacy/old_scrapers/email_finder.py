import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Set
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from core.utils import get_random_user_agent, EMAIL_REGEX

class EmailFinder:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": get_random_user_agent()},
            follow_redirects=True,
            timeout=10.0
        )

    async def find_emails_from_url(self, url: str) -> List[str]:
        """Crawl website for emails, with Playwright fallback."""
        emails: Set[str] = set()
        if not url: return []
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        try:
            # Plan A: Fast HTTP Scrape
            emails.update(await self._fast_scrape(url))
        except Exception as e:
            print(f"Fast scrape failed for {url}: {e}")
            pass

        # Plan B: If nothing found, use Plan B (Playwright)
        if not emails:
            try:
                emails.update(await self._browser_scrape(url))
            except Exception as e:
                print(f"Browser scrape failed for {url}: {e}")
                pass

        return list(emails)

    async def _fast_scrape(self, url: str) -> Set[str]:
        emails = set()
        resp = await self.client.get(url)
        if resp.status_code == 200:
            emails.update(self._extract_from_text(resp.text))
            base_domain = url.split('//')[-1].split('/')[0]
            soup = BeautifulSoup(resp.text, 'html.parser')
            target_pages = []
            for a in soup.find_all('a', href=True):
                href = a['href'].lower()
                if any(x in href for x in ['contact', 'about', 'support']):
                    if href.startswith('/'): target_pages.append(f"https://{base_domain}{href}")
                    elif href.startswith('http') and base_domain in href: target_pages.append(a['href'])
            
            # Scrape subpages
            tasks = [self.client.get(p) for p in set(target_pages[:3])]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for r in responses:
                if isinstance(r, httpx.Response) and r.status_code == 200:
                    emails.update(self._extract_from_text(r.text))
        return emails

    async def _browser_scrape(self, url: str) -> Set[str]:
        emails = set()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=get_random_user_agent())
            await Stealth().apply_stealth_async(page)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait a bit for JS to render some components just in case
                await asyncio.sleep(3)
                content = await page.content()
                emails.update(self._extract_from_text(content))
                # Click a contact page if found (skip for social networks)
                if "instagram.com" not in url and "facebook.com" not in url:
                    contact_link = page.get_by_role("link", name=re.compile("contact", re.IGNORECASE)).first
                    if await contact_link.is_visible():
                        await contact_link.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(2)
                        content = await page.content()
                        emails.update(self._extract_from_text(content))
            finally:
                await browser.close()
        return emails

    def _extract_from_text(self, text: str) -> List[str]:
        return re.findall(EMAIL_REGEX, text)

    async def close(self):
        await self.client.aclose()
