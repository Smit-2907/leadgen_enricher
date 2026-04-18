import asyncio
import time
from pipelines.no_website_enrichment import no_website_enrichment

async def test_case(name, loc):
    print(f"\n🚀 Testing: {name} in {loc}...")
    start = time.time()
    try:
        result = await no_website_enrichment(name, loc)
        elapsed = time.time() - start
        print(f"✅ Completed in {elapsed:.2f}s")
        print(f"Emails found: {result['emails']}")
        print(f"Socials found: {result['socials']}")
        print(f"Sources checked: {result['sources_checked']}")
        print(f"Confidence score: {result['confidence_score']}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

async def run_tests():
    # Test 1: Indian Cafe
    await test_case("Hygge Ahmedabad", "Ahmedabad")
    
    # Test 2: Local Plumber (Hard case)
    await test_case("Perfect Plumbers", "London")

if __name__ == "__main__":
    asyncio.run(run_tests())
