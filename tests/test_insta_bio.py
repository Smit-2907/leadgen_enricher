import asyncio
from scrapers.social_platforms import SocialPlatformScraper

async def test_fallback():
    scraper = SocialPlatformScraper()
    # Test Instagram domain scrape logic via stealth scraper rather than regular html
    email = await scraper.scrape_bio("https://www.instagram.com/guligulipets")
    print(f"Insta Bio Scraper Email found: {email}")

if __name__ == "__main__":
    asyncio.run(test_fallback())