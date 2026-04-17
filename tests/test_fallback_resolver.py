"""
Integration test for fallback_identity_resolver.
Tests gate check, real search, matching, and extraction.
"""
import asyncio
import json
from fallback_identity_resolver.resolver import resolve_missing_identity


async def test_gate_blocks_when_data_exists():
    """Must return None when phone exists."""
    result = await resolve_missing_identity(
        "Any Business", "Some City",
        _phone="09999999999",   # gate should block
        _website=None,
    )
    assert result is None, "Gate check failed — should have returned None"
    print("✅ Gate check: PASSED — exits immediately when phone exists")


async def test_gate_blocks_when_website_exists():
    """Must return None when website exists."""
    result = await resolve_missing_identity(
        "Any Business", "Some City",
        _phone=None,
        _website="https://example.com",  # gate should block
    )
    assert result is None, "Gate check failed — should have returned None"
    print("✅ Gate check: PASSED — exits immediately when website exists")


async def test_real_fallback_india():
    """Real test: a small Indian business with no website/phone."""
    print("\n🔍 Running real fallback for: 7th Heaven Event Planners, Kolkata")
    result = await resolve_missing_identity(
        business_name="7th Heaven Event Planners",
        city="Kolkata",
        country="india",
        _website=None,
        _phone=None,
    )
    assert result is not None, "Expected a FallbackResult, got None"
    print(f"   Emails found   : {result.emails}")
    print(f"   Socials found  : {json.dumps({k:v for k,v in result.socials.items() if v}, indent=2)}")
    print(f"   Directories    : {result.directories}")
    print(f"   Best Method    : {result.best_contact_method}")
    print(f"   Confidence     : {result.confidence_score}")
    print(f"   Message        : {result.message}")
    print(f"   Sources        : {' → '.join(result.sources_checked)}")
    print(f"   Output JSON    :\n{json.dumps(result.to_dict(), indent=2)}")


async def main():
    await test_gate_blocks_when_data_exists()
    await test_gate_blocks_when_website_exists()
    await test_real_fallback_india()


if __name__ == "__main__":
    asyncio.run(main())
