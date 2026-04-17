"""
Email Guesser — generates pattern-based emails from a known domain and validates
them via MX record check. No SMTP probing, just DNS.
"""
import asyncio
import re
from typing import List, Optional
import httpx
import dns.resolver

COMMON_PREFIXES = ["info", "contact", "hello", "enquiry", "support", "admin", "sales", "business"]


def _extract_domain(website: str) -> Optional[str]:
    match = re.search(r'https?://(?:www\.)?([^/]+)', website)
    return match.group(1).lower() if match else None


def _has_mx_record(domain: str) -> bool:
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


async def guess_emails(website: str) -> List[str]:
    """Generate common pattern emails for a domain, return those with valid MX."""
    if not website:
        return []

    domain = _extract_domain(website)
    if not domain:
        return []

    # Check in thread since dns is blocking
    has_mx = await asyncio.to_thread(_has_mx_record, domain)
    if not has_mx:
        return []

    guesses = [f"{prefix}@{domain}" for prefix in COMMON_PREFIXES]
    return guesses  # Return all; caller can pick top ones
