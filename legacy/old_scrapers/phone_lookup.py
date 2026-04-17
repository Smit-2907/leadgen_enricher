import asyncio
from typing import List
from duckduckgo_search import DDGS
from core.utils import get_random_user_agent

class PhoneLookup:
    async def reverse_search(self, phone: str) -> List[str]:
        """Perform a reverse search on a phone number to find linked social profiles."""
        if not phone:
            return []
            
        results = []
        # Search for phone on major platforms
        query = f'"{phone}" facebook OR instagram OR linkedin'
        
        try:
            with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                search_results = list(ddgs.text(query, max_results=5))
                for r in search_results:
                    href = r['href'].lower()
                    if any(x in href for x in ['facebook.com', 'instagram.com', 'linkedin.com']):
                        results.append(r['href'])
        except:
            pass
            
        return results
