import asyncio
from typing import List, Optional
from duckduckgo_search import DDGS
from core.utils import get_random_user_agent, EMAIL_REGEX, is_valid_match
import httpx
import re

class IndiaMartScraper:
    async def find_contact_info(self, business_name: str, location: str) -> List[str]:
        """Search IndiaMART and extract emails."""
        emails = []
        query = f'site:indiamart.com "{business_name}" "{location}"'
        
        try:
            with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                results = list(ddgs.text(query, max_results=3))
                for r in results:
                    # Sniff snippets for emails
                    emails.extend(re.findall(EMAIL_REGEX, r['body']))
                    
                    # If we find a specific company page, try a quick scrape
                    if "/proddetail/" in r['href'] or "/company/" in r['href']:
                        async with httpx.AsyncClient(headers={"User-Agent": get_random_user_agent()}) as client:
                            resp = await client.get(r['href'], timeout=10.0)
                            if resp.status_code == 200:
                                emails.extend(re.findall(EMAIL_REGEX, resp.text))
        except:
            pass
            
        return list(set(emails))
