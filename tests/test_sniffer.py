import asyncio
from scrapers.directory_sniffer import DirectorySniffer

async def test():
    print("Testing DirectorySniffer")
    sniffer = DirectorySniffer()
    emails = await sniffer.hunt_emails("Guli Guli Pet Shop", "ahmedabad")
    print(f"DirectorySniffer emails: {emails}")

if __name__ == "__main__":
    asyncio.run(test())