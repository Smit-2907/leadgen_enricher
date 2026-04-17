import asyncio
from duckduckgo_search import DDGS
from googlesearch import search as google_search

def test_google():
    print("\nTesting Google for Guli Guli Email")
    query = "Guli Guli Pet Shop ahmedabad instagram OR facebook"
    try:
        for url in google_search(query, num_results=5):
            print(f"G-Found: {url}")
    except Exception as e:
        print(f"Google Error: {e}")

if __name__ == "__main__":
    test_google()