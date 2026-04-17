import asyncio
from scrapers.email_finder import EmailFinder

async def test_fallback():
    finder = EmailFinder()
    # Test Instagram domain scrape logic
    emails = await finder.find_emails_from_url("https://www.instagram.com/guligulipets")
    print(f"Insta Emails found: {emails}")

if __name__ == "__main__":
    asyncio.run(test_fallback())