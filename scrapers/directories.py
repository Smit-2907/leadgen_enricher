import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from core.models import SocialProfile
from core.utils import get_random_user_agent

class DirectoryScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": get_random_user_agent()},
            follow_redirects=True,
            timeout=15.0
        )

    async def search_justdial(self, business_name: str, location: str) -> List[str]:
        """Search JustDial (India) for the business listing."""
        results = []
        # Query format: https://www.justdial.com/Location/Business-Name
        query_city = location.replace(" ", "-")
        query_name = business_name.replace(" ", "-")
        url = f"https://www.justdial.com/{query_city}/{query_name}"
        
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if any(x in href for x in ['facebook.com', 'instagram.com', 'linkedin.com']):
                        results.append(href)
        except Exception as e:
            print(f"JustDial scraper error: {e}")
        return results

    async def search_sulekha(self, business_name: str, location: str) -> List[str]:
        """Search Sulekha (India) for business listings."""
        results = []
        url = f"https://www.sulekha.com/search?q={business_name} {location}"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                pass 
        except Exception as e:
            print(f"Sulekha scraper error: {e}")
        return results

    async def close(self):
        await self.client.aclose()
