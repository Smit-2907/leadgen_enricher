import asyncio
from pipelines.resolver import resolve_identity
import time

async def test():
    # Test 2: No-website lead (hardest case)
    t = time.time()
    r = await resolve_identity("Guli Guli Pet Shop", "Ahmedabad", country="india", phone="09909992027")
    print(f"\nTime: {time.time()-t:.1f}s")
    print("Emails:", r.emails)
    print("Socials:", {k: v for k, v in r.socials.items() if v})
    print("Best:", r.best_contact_method)
    print("Reason:", r.reasoning)
    print("Sources:", r.sources_used)

asyncio.run(test())