import asyncio
from duckduckgo_search import DDGS
from googlesearch import search as google_search

def test_ddgs():
    print("Testing DDGS for Guli Guli")
    query = '"Guli Guli Pet Shop" "ahmedabad" "@gmail.com" OR "mail" OR "contact"'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            for r in results:
                print(f"[{r.get('title')}] {r.get('body')} - {r.get('href')}")
    except Exception as e:
        print(f"DDG Error: {e}")

def test_google():
    print("\nTesting Google for Guli Guli")
    query = '"Guli Guli Pet Shop" "ahmedabad" "@gmail.com" OR "mail" OR "contact"'
    try:
        for url in google_search(query, num_results=5):
            print(f"G-Found: {url}")
    except Exception as e:
        print(f"Google Error: {e}")

if __name__ == "__main__":
    test_ddgs()
    test_google()
