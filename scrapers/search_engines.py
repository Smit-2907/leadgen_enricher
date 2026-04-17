import asyncio
from typing import List, Dict
from duckduckgo_search import DDGS
from googlesearch import search as google_search
from core.models import SocialProfile
from core.utils import get_random_user_agent, random_delay

class SearchEngineScraper:
    def __init__(self):
        # We'll use a new DDGS instance per search to avoid session reuse issues
        pass

    async def find_social_urls(self, business_name: str, location: str) -> List[SocialProfile]:
        """Parallel search for social profiles with fallbacks."""
        platforms = ["instagram", "facebook", "linkedin"]
        tasks = []
        
        for platform in platforms:
            # Task 1: Strict Dork
            tasks.append(self._search_ddgs(business_name, location, platform, use_dork=True))
            # Task 2: Broad Search
            tasks.append(self._search_ddgs(business_name, location, platform, use_dork=False))
            # Task 3: Google (Last resort, staggered)
            tasks.append(self._search_google(business_name, location, platform))

        results = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate
        profiles = []
        seen_urls = set()
        for res_list in results:
            if not res_list: continue
            for profile in res_list:
                url_str = str(profile.url).lower().rstrip('/')
                if url_str not in seen_urls:
                    profiles.append(profile)
                    seen_urls.add(url_str)
        
        return profiles

    async def _search_ddgs(self, business_name: str, location: str, platform: str, use_dork: bool) -> List[SocialProfile]:
        profiles = []
        if use_dork:
            query = f'site:{platform}.com "{business_name}" "{location}"'
        else:
            query = f'"{business_name}" "{location}" {platform} profile'
            
        try:
            await random_delay(0.5, 1.5)
            with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    for r in results:
                        profiles.append(SocialProfile(
                            platform=platform,
                            url=r['href'],
                            name_on_platform=r.get('title', business_name),
                            confidence_score=0.8 if use_dork else 0.5
                        ))
        except Exception as e:
            # Silent fail for DDG to avoid cluttering logs
            pass
        return profiles

    async def _search_google(self, business_name: str, location: str, platform: str) -> List[SocialProfile]:
        profiles = []
        query = f'site:{platform}.com "{business_name}" "{location}"'
        try:
            # Stagger Google requests to avoid 429
            await random_delay(2.0, 4.0)
            # googlesearch-python uses a generator
            gen = google_search(query, num_results=2)
            results = await asyncio.to_thread(lambda: list(gen))
            if results:
                for url in results:
                    profiles.append(SocialProfile(
                        platform=platform,
                        url=url,
                        name_on_platform=business_name, # Default to biz name
                        confidence_score=0.9
                    ))
        except Exception as e:
            if "429" not in str(e):
                print(f"Google error for {platform}: {e}")
        return profiles
