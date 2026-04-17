import asyncio
import re
from typing import List
from duckduckgo_search import DDGS
from core.utils import get_random_user_agent, EMAIL_REGEX, random_delay

class DirectorySniffer:
    async def hunt_emails(self, business_name: str, location: str) -> List[str]:
        """Search across many business directories and extract from snippets."""
        emails = []
        # Target specific directory platforms that index well
        directories = [
            "sulekha.com", "asklaila.com", "tradeindia.com", 
            "yelp.in", "yellowpages.in", "crunchbase.com", 
            "zoominfo.com", "rocketreach.co"
        ]
        
        # Combine directories into groups to save on search calls
        for i in range(0, len(directories), 4):
            site_query = " OR ".join([f"site:{d}" for d in directories[i:i+4]])
            query = f'({site_query}) "{business_name}" "{location}"'
            
            try:
                await random_delay(0.5, 1.5)
                with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                    for r in results:
                        found = re.findall(EMAIL_REGEX, r.get('body', ''))
                        if found:
                            emails.extend(found)
            except Exception:
                pass
                
        return list(set([e.lower() for e in emails]))
