import asyncio
import time
from pipelines.resolver import resolve_identity
import sys

async def main():
    print("Testing integration...")
    b_name = "Tech Solutions"
    city = "Bangalore"
    
    t0 = time.time()
    result = await resolve_identity(b_name, city, country="india", website=None)
    
    print(f"Time Taken: {time.time() - t0:.2f}s")
    print(f"Emails: {result.emails}")
    print(f"Sources: {result.sources_used}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.best_contact_method}")

if __name__ == "__main__":
    asyncio.run(main())
