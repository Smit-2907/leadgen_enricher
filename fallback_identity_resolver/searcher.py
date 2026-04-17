"""
Fallback Search — Google-free web search via DuckDuckGo.
Runs 5 targeted queries in parallel threads, returns top 15 URLs.

No imports from existing pipeline.
"""
import asyncio
import random
import re
from typing import List
from ddgs import DDGS
from fallback_identity_resolver.models import FallbackCandidate

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_NOISE_MARKERS = frozenset([
    "/explore/tags/", "/p/", "/reel/", "/events/", "/groups/",
    "status/", "/pin/", "watch?v=", "/posts/",
])

_EXCLUDE_EMAIL_PARTS = frozenset([
    "domainsbyproxy", "privacy", "whoisguard", "abuse", "registrar",
    "godaddy", "namecheap", "noreply", "no-reply", "example.com", "sentry",
])


def _clean_business_name(name: str) -> str:
    """Strip unicode junk, legal suffixes, pipe-separated tags."""
    name = re.sub(r'[^\x00-\x7F]+', ' ', name.lower())
    name = re.sub(r'\|\|.*', '', name)
    for s in [' llp', ' pvt ltd', ' private limited', ' inc.', ' inc',
              ' corp', ' co.', ' ltd', ' limited']:
        name = name.replace(s, '')
    return ' '.join(name.split()).strip().title()


def _short_name(clean: str) -> str:
    return ' '.join(clean.split()[:3])


def is_noise(url: str) -> bool:
    low = url.lower()
    return any(m in low for m in _NOISE_MARKERS)


def extract_emails_from_text(text: str) -> List[str]:
    found = _EMAIL_REGEX.findall(text)
    return [e.lower() for e in found
            if not any(x in e.lower() for x in _EXCLUDE_EMAIL_PARTS)]


def _build_queries(business_name: str, city: str) -> List[str]:
    cn = _clean_business_name(business_name)
    return [
        f'"{cn}" "{city}"',
        f'"{cn}" "{city}" contact',
        f'"{cn}" "{city}" instagram',
        f'"{cn}" "{city}" facebook',
        f'"{cn}" "{city}" linkedin',
    ]


def _ddgs_sync(query: str, max_results: int = 5) -> List[dict]:
    """Blocking DDGS call — runs inside asyncio.to_thread."""
    try:
        ua = random.choice(_USER_AGENTS)
        with DDGS(headers={"User-Agent": ua}) as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []


async def _run_query_with_timeout(query: str, max_results: int = 5) -> List[dict]:
    """Run one DDGS query in a thread with an 8-second hard cap."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_ddgs_sync, query, max_results),
            timeout=8.0
        )
    except (asyncio.TimeoutError, Exception):
        return []


async def run_fallback_search(business_name: str, city: str) -> List[FallbackCandidate]:
    """
    Run 5 queries in parallel threads. Collect, deduplicate, and return
    up to 15 FallbackCandidate objects.
    """
    queries = _build_queries(business_name, city)
    tasks = [_run_query_with_timeout(q) for q in queries]
    batches = await asyncio.gather(*tasks)

    seen: set[str] = set()
    candidates: List[FallbackCandidate] = []

    for batch in batches:
        for hit in batch:
            url = hit.get("href", "")
            if not url or url in seen or is_noise(url):
                continue
            seen.add(url)
            candidates.append(FallbackCandidate(
                url=url,
                title=hit.get("title", ""),
                snippet=hit.get("body", ""),
            ))
            if len(candidates) >= 15:
                return candidates

    return candidates
