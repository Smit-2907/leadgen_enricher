"""
Email Guesser — generates and MX-validates pattern emails from a domain.

Rules from spec:
  IF domain found → generate info@, contact@, hello@
  IF no domain    → do NOT generate anything

No imports from existing pipeline.
"""
import asyncio
import re
from typing import List, Optional

_PREFIXES = ["info", "contact", "hello", "enquiry", "support", "admin", "sales"]


def _extract_domain_from_url(url: str) -> Optional[str]:
    match = re.search(r'https?://(?:www\.)?([^/?#]+)', url)
    if not match:
        return None
    domain = match.group(1).lower()
    # Reject social/directory domains — we only want business domains
    _skip = {"instagram.com", "facebook.com", "linkedin.com", "justdial.com",
              "sulekha.com", "indiamart.com", "yelp.com", "yell.com",
              "yellowpages.com", "yellowpages.com.au", "twitter.com"}
    if any(domain.endswith(s) for s in _skip):
        return None
    return domain


def _check_mx_sync(domain: str) -> bool:
    """Blocking MX DNS check — intended for asyncio.to_thread."""
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


async def guess_emails_from_domain(website_url: Optional[str]) -> List[str]:
    """
    Generate pattern-based guesses for a domain found in any accepted candidate.
    Returns empty list if no valid domain found or MX check fails.
    """
    if not website_url:
        return []

    domain = _extract_domain_from_url(website_url)
    if not domain:
        return []

    has_mx = await asyncio.to_thread(_check_mx_sync, domain)
    if not has_mx:
        return []

    return [f"{prefix}@{domain}" for prefix in _PREFIXES]
