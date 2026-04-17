import asyncio
from scrapers.search_engines import SearchEngineScraper

async def test():
    print("Testing Deep Web Email Dorking")
    scraper = SearchEngineScraper()
    emails = await scraper.find_emails_via_dork("Guli Guli Pet Shop", "ahmedabad", "09909992027")
    print(f"Dorking emails: {emails}")

if __name__ == "__main__":
    asyncio.run(test())