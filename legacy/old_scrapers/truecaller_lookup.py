import asyncio
import re
from typing import List, Optional
from duckduckgo_search import DDGS
from core.utils import get_random_user_agent

class TruecallerLookup:
    async def reverse_phone_search(self, phone: str) -> Optional[str]:
        """Search for a phone number on Truecaller via search dorks."""
        if not phone: return None
        
        # Clean phone (remove spaces/plus)
        clean_phone = re.sub(r"\D", "", phone)
        query = f'site:truecaller.com "{clean_phone}"'
        
        try:
            with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    # Sniff first result for the name/tag
                    title = results[0]['title']
                    # Typically: "Name - Truecaller" or "Phone Number - Name - Truecaller"
                    if "Truecaller" in title:
                        return title.split('-')[0].strip()
        except:
            pass
        return None
