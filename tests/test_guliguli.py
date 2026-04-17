import asyncio
from scrapers.email_finder import EmailFinder
from core.models import LeadIn
from core.engine import EnrichmentEngine

async def test_guliguli():
    url = "https://guligulipets.in/"
    print(f"Testing URL: {url}")
    
    engine = EnrichmentEngine()
    lead = LeadIn(
        business_name="𝗚𝘂𝗹𝗶 𝗚𝘂𝗹𝗶 𝗣𝗲𝘁 𝗦𝗵𝗼𝗽 || Best Pet Shop, Pet Food Shop",
        location="ahmedabad, gujarat, india",
        website="https://guligulipets.in/"
    )
    result = await engine.enrich_lead(lead)
    print(f"Emails found: {result.emails}")
    print(f"Socials found: {len(result.social_profiles)}")
    for p in result.social_profiles:
        print(f"  {p.url}")
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(test_guliguli())
