import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Set
from core.utils import get_random_user_agent, EMAIL_REGEX

class EmailFinder:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": get_random_user_agent()},
            follow_redirects=True,
            timeout=10.0
        )

    async def find_emails_from_url(self, url: str) -> List[str]:
        """Crawl common pages on the website to find emails."""
        emails: Set[str] = set()
        if not url:
            return []

        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        # Pages to check
        target_pages = [url]
        base_domain = url.split('//')[-1].split('/')[0]

        try:
            # First pass: main page
            main_resp = await self.client.get(url)
            if main_resp.status_code == 200:
                emails.update(self._extract_from_text(main_resp.text))
                
                # Look for contact/about links
                soup = BeautifulSoup(main_resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href'].lower()
                    if any(x in href for x in ['contact', 'about', 'support', 'info']):
                        if href.startswith('/'):
                            target_pages.append(f"https://{base_domain}{href}")
                        elif href.startswith('http') and base_domain in href:
                            target_pages.append(a['href'])

            # Second pass: sub-pages
            target_pages = list(set(target_pages))[:5] # Limit to 5 pages
            tasks = [self.client.get(p) for p in target_pages if p != url]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for resp in responses:
                if isinstance(resp, httpx.Response) and resp.status_code == 200:
                    emails.update(self._extract_from_text(resp.text))

        except Exception as e:
            print(f"EmailFinder error for {url}: {e}")

        return list(emails)

    def _extract_from_text(self, text: str) -> List[str]:
        return re.findall(EMAIL_REGEX, text)

    async def close(self):
        await self.client.aclose()
