import asyncio
from scrapers.search_engines import SearchEngineScraper
from scrapers.directory_sniffer import DirectorySniffer

async def test_fallback():
    engine = SearchEngineScraper()
    sniffer = DirectorySniffer()
    res1 = await engine.find_emails_via_dork("𝗚𝘂𝗹𝗶 𝗚𝘂𝗹𝗶 𝗣𝗲𝘁 𝗦𝗵𝗼𝗽", "ahmedabad", "09909992027")
    res2 = await sniffer.hunt_emails("𝗚𝘂𝗹𝗶 𝗚𝘂𝗹𝗶 𝗣𝗲𝘁 𝗦𝗵𝗼𝗽", "ahmedabad")
    print(f"Dork: {res1}, Sniff: {res2}")

if __name__ == "__main__":
    asyncio.run(test_fallback())