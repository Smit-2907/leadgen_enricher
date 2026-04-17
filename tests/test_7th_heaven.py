import asyncio
from core.utils import clean_business_name, is_valid_match
from scrapers.search_engines import SearchEngineScraper

async def test():
    name = "7th Heaven Event Planners LLP"
    loc = "Kolkata"
    clean = clean_business_name(name)
    print(f"Original: {name} | Cleaned: {clean}")
    
    scraper = SearchEngineScraper()
    results = await scraper.find_social_urls(name, loc)
    print(f"\nFinal Results returned to engine: {len(results)}")
    for r in results:
        print(f" - {r.platform}: {r.url} (Meta: {r.name_on_platform})")

if __name__ == "__main__":
    asyncio.run(test())
