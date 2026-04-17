import asyncio
from pipelines.resolver import resolve_identity
import time

async def test():
    t = time.time()
    r = await resolve_identity("7th Heaven Event Planners LLP", "kolkata", website="https://7thheavenweddings.com/")
    print(f"Time: {time.time()-t:.1f}s")
    print("Emails:", r.emails)
    print("Socials:", {k: v for k, v in r.socials.items() if v})
    print("Best:", r.best_contact_method)
    print("Reason:", r.reasoning)

asyncio.run(test())