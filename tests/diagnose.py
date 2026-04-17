import asyncio
from duckduckgo_search import DDGS
from googlesearch import search as google_search

async def diagnose():
    name = "Sunrise Dental Clinic"
    loc = "Pune"
    query = f'site:instagram.com "{name}" "{loc}"'
    
    print(f"--- Testing DuckDuckGo for: {query} ---")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            for r in results:
                print(f"Found: {r['title']} -> {r['href']}")
    except Exception as e:
        print(f"DDG Error: {e}")

    print(f"\n--- Testing Google for: {query} ---")
    try:
        results = google_search(query, num_results=3)
        for url in results:
            print(f"Found URL: {url}")
    except Exception as e:
        print(f"Google Error: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
