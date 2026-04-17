import asyncio
from typing import List, Dict
from duckduckgo_search import DDGS
from googlesearch import search as google_search
from core.models import SocialProfile
from core.utils import get_random_user_agent, random_delay, clean_business_name

class SearchEngineScraper:
    def __init__(self):
        # We'll use a new DDGS instance per search to avoid session reuse issues
        pass

    async def find_social_urls(self, business_name: str, location: str) -> List[SocialProfile]:
        """Parallel search for social profiles with name-shortening fallbacks."""
        clean_name = clean_business_name(business_name)
        platforms = ["instagram", "facebook", "linkedin", "pinterest", "twitter"]
        tasks = []
        
        # We try both the full clean name and a shortened version (first 3 words)
        short_name = " ".join(clean_name.split()[:3])
        search_variations = [business_name, clean_name]
        if short_name != clean_name:
            search_variations.append(short_name)

        for name_var in search_variations:
            for platform in platforms:
                tasks.append(self._search_ddgs(name_var, location, platform, use_dork=(name_var == business_name)))
                tasks.append(self._search_google(name_var, location, platform))

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
                        url_str = r['href'].lower()
                        if platform not in url_str:
                            continue
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
                    url_str = url.lower()
                    if platform not in url_str:
                        continue
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

    async def find_emails_via_dork(self, business_name: str, location: str, phone: str = None) -> List[str]:
        """Search for business emails scattered across web snippets (directories, ads, posts)."""
        emails = []
        clean_name = clean_business_name(business_name)
        queries = [
            f'"{clean_name}" "{location}" "@gmail.com" OR "@yahoo.com" OR "@hotmail.com"'
        ]
        if phone:
            queries.append(f'"{phone}" "@gmail.com" OR "email"')
            
        import re
        from core.utils import EMAIL_REGEX

        try:
            for query in queries:
                await random_delay(0.5, 1.5)
                with DDGS(headers={"User-Agent": get_random_user_agent()}) as ddgs:
                    results = list(ddgs.text(query, max_results=3))
                    for r in results:
                        # Extract directly from search snippet
                        body_emails = re.findall(EMAIL_REGEX, r.get('body', ''))
                        if body_emails:
                            emails.extend([e.lower() for e in body_emails])
        except Exception:
            pass
            
        return list(set(emails))
