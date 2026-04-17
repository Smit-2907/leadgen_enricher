import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_ddgs_html():
    print("Testing DDGS HTML")
    query = "Guli Guli pet shop"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})
            print(f"Status: {resp.status_code}")
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", class_="result__url"):
                print(a.get("href"))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ddgs_html())