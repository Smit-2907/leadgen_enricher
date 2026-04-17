"""
Search Layer — generates and runs parallel queries against DuckDuckGo.
Returns raw DiscoveredURL objects for the matching engine.
"""
import asyncio
import re
from typing import List
from ddgs import DDGS
from search.models import BusinessInput, DiscoveredURL, Country
from search.utils import random_ua, jitter

PLATFORM_DOMAINS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "twitter": "twitter.com",
    "pinterest": "pinterest.com",
}

COUNTRY_DIRECTORIES: dict[Country, list[str]] = {
    "india": ["justdial.com", "sulekha.com", "indiamart.com", "tradeindia.com", "asklaila.com"],
    "usa":   ["yelp.com", "yellowpages.com", "manta.com", "chamberofcommerce.com"],
    "uk":    ["yell.com", "companieshouse.gov.uk", "cylex.co.uk"],
    "australia": ["yellowpages.com.au", "truelocal.com.au", "whereis.com"],
    "unknown": ["yelp.com", "yellowpages.com"],
}


def _build_queries(biz: BusinessInput) -> List[dict]:
    """Generate all search query strings with metadata."""
    cn = biz.clean_name()
    sn = biz.short_name()
    city = biz.city
    phone = biz.phone or ""
    queries = []

    # Core email-hunting queries
    queries += [
        {"q": f'"{cn}" "{city}" contact email', "intent": "email"},
        {"q": f'"{cn}" "{city}" "@gmail.com" OR "@yahoo.com"', "intent": "email"},
        {"q": f'"{sn}" "{city}" email', "intent": "email"},
    ]

    # Phone-based cross reference
    if phone:
        clean_phone = re.sub(r"[^\d+]", "", phone)
        queries += [
            {"q": f'"{clean_phone}"', "intent": "phone"},
            {"q": f'"{clean_phone}" email', "intent": "email"},
        ]

    # Social platform dorks
    for platform, domain in PLATFORM_DOMAINS.items():
        queries.append({"q": f'site:{domain} "{cn}"', "intent": "social", "platform": platform})
        if sn != cn:
            queries.append({"q": f'site:{domain} "{sn}"', "intent": "social", "platform": platform})

    # Country-specific directories
    dirs = COUNTRY_DIRECTORIES.get(biz.country, COUNTRY_DIRECTORIES["unknown"])
    site_query = " OR ".join([f"site:{d}" for d in dirs[:3]])
    queries.append({"q": f'({site_query}) "{cn}" "{city}"', "intent": "directory"})
    if sn != cn:
        queries.append({"q": f'({site_query}) "{sn}" "{city}"', "intent": "directory"})

    return queries


def _ddgs_search_sync(query: str, max_results: int) -> list:
    """Synchronous DDGS call — meant to be run in a thread."""
    try:
        with DDGS(headers={"User-Agent": random_ua()}) as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []


async def _run_single_query(q_meta: dict, max_results: int = 5) -> List[DiscoveredURL]:
    """Run one DDGS search in a thread and return DiscoveredURLs."""
    await jitter(0.1, 0.4)
    hits = await asyncio.to_thread(_ddgs_search_sync, q_meta["q"], max_results)
    results = []
    for h in hits:
        results.append(DiscoveredURL(
            url=h["href"],
            source="ddgs",
            snippet=h.get("body", ""),
            platform=q_meta.get("platform"),
        ))
    return results


async def run_all_queries(biz: BusinessInput) -> List[DiscoveredURL]:
    """Run all queries in parallel and return deduplicated results."""
    queries = _build_queries(biz)
    tasks = [_run_single_query(q) for q in queries]
    batches = await asyncio.gather(*tasks)

    seen_urls: set[str] = set()
    all_results: List[DiscoveredURL] = []
    for batch in batches:
        for r in batch:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)

    return all_results
