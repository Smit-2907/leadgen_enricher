import asyncio
from duckduckgo_search import DDGS
from googlesearch import search as google_search

def test_ddgs():
    print("Testing DDGS Broad")
    query = "Guli Guli pet shop"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            for r in results:
                print(f"[{r.get('title')}] {r.get('href')}")
    except Exception as e:
        print(f"DDG Error: {e}")

if __name__ == "__main__":
    test_ddgs()