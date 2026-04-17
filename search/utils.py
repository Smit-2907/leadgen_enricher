"""
Shared utilities: user-agent rotation, delays, email regex.
"""
import asyncio
import random
import re
from typing import List

EMAIL_REGEX = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

NOISE_URL_MARKERS = [
    "/explore/tags/", "/p/", "/reel/", "/events/", "/groups/",
    "status/", "/pin/", "watch?v=", "/posts/",
]

EXCLUDE_EMAILS = [
    "domainsbyproxy", "privacy", "whoisguard", "abuse", "registrar",
    "godaddy", "namecheap", "enom", "tucows", "hugedomains",
    "cloudflare", "noreply", "no-reply", "example.com",
]


def random_ua() -> str:
    return random.choice(USER_AGENTS)


async def jitter(min_s: float = 0.5, max_s: float = 1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))


def extract_emails(text: str) -> List[str]:
    found = re.findall(EMAIL_REGEX, text)
    return [e.lower() for e in found if not any(x in e.lower() for x in EXCLUDE_EMAILS)]


def is_noise_url(url: str) -> bool:
    url_lower = url.lower()
    return any(m in url_lower for m in NOISE_URL_MARKERS)


def get_domain(url: str) -> str:
    """Extract base domain from URL."""
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return match.group(1).lower() if match else ""
