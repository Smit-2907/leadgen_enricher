import asyncio
from duckduckgo_search import DDGS
from googlesearch import search as google_search

async def diagnose_specific():
    name = "7th Heaven Event Planners LLP"
    loc = "Kolkata"
    # Try different query styles
    queries = [
        f'site:instagram.com "{name}" "{loc}"',
        f'"{name}" Kolkata Instagram',
        f'"{name}" Kolkata Facebook',
        f'7th Heaven Event Planners Kolkata'
    ]
    
    for query in queries:
        print(f"\n--- Testing DDG: {query} ---")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    print(f"Found: {r['title']} -> {r['href']}")
        except Exception as e:
            print(f"DDG Error: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_specific())
