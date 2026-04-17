"""
Data Extractor — platform-specific scrapers for accepted candidates.

Instagram  → scrape bio, extract email via regex
Facebook   → scrape About section, extract email/phone
LinkedIn   → extract company info (public only)
Directories → extract structured email/phone from HTML

Strategy:
  1. Try fast httpx GET with browser headers
  2. If JS-heavy (Instagram/Facebook), use Playwright stealth
  3. Strict 10s timeout per page — never block the pipeline

No imports from existing pipeline.
"""
import asyncio
import re
from typing import Optional, List
import httpx
from bs4 import BeautifulSoup

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{4,10}")

_EXCLUDE_EMAIL_PARTS = frozenset([
    "domainsbyproxy", "privacy", "whoisguard", "abuse", "registrar",
    "godaddy", "namecheap", "noreply", "no-reply", "example.com", "sentry",
])

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _clean_emails(raw: List[str]) -> List[str]:
    return sorted(set(
        e.lower() for e in raw
        if not any(x in e.lower() for x in _EXCLUDE_EMAIL_PARTS)
    ))


async def _try_http(url: str, timeout: float = 8.0) -> str:
    """Simple async HTTP fetch. Returns HTML or empty string."""
    try:
        async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return ""


async def _try_playwright(url: str, timeout_ms: int = 10000) -> str:
    """Playwright stealth fetch — only used when HTTP fails."""
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=_HEADERS["User-Agent"])
                await Stealth().apply_stealth_async(page)
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await asyncio.sleep(2)
                return await page.content()
            finally:
                await browser.close()
    except Exception:
        return ""


# ─── Platform-Specific Extractors ─────────────────────────────────────────────

async def extract_instagram(url: str) -> dict:
    """Scrape Instagram profile bio for emails."""
    html = await _try_playwright(url, timeout_ms=12000)
    emails = _clean_emails(_EMAIL_RE.findall(html))
    return {"emails": emails, "url": url if html else None}


async def extract_facebook(url: str) -> dict:
    """Scrape Facebook About section for email and phone."""
    # Try public About URL first
    about_url = url.rstrip("/") + "/about"
    html = await _try_playwright(about_url, timeout_ms=12000)
    if not html:
        html = await _try_playwright(url, timeout_ms=12000)

    emails = _clean_emails(_EMAIL_RE.findall(html))
    # Extract phone numbers from About content
    soup = BeautifulSoup(html, "lxml")
    body_text = soup.get_text(" ", strip=True) if html else ""
    phones = _PHONE_RE.findall(body_text)[:2]  # top 2 numbers

    return {"emails": emails, "phones": phones, "url": url if html else None}


async def extract_linkedin(url: str) -> dict:
    """Extract LinkedIn public company info (HTTP only — no login)."""
    html = await _try_http(url)
    if not html:
        return {"emails": [], "url": None}

    soup = BeautifulSoup(html, "lxml")
    emails = _clean_emails(_EMAIL_RE.findall(soup.get_text()))
    return {"emails": emails, "url": url}


async def extract_directory(url: str) -> dict:
    """Extract email and phone from a directory listing page."""
    html = await _try_http(url)
    if not html:
        html = await _try_playwright(url, timeout_ms=10000)
    if not html:
        return {"emails": [], "phones": [], "url": None}

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    emails = _clean_emails(_EMAIL_RE.findall(text))
    phones = _PHONE_RE.findall(text)[:3]

    return {"emails": emails, "phones": phones, "url": url}


# ─── Dispatcher ───────────────────────────────────────────────────────────────

async def extract_from_candidate(category: str, url: str) -> dict:
    """Route to the correct extractor with a hard 12s timeout."""
    extractor_map = {
        "instagram": extract_instagram,
        "facebook": extract_facebook,
        "linkedin": extract_linkedin,
        "directory": extract_directory,
    }
    fn = extractor_map.get(category, extract_directory)
    try:
        return await asyncio.wait_for(fn(url), timeout=12.0)
    except (asyncio.TimeoutError, Exception):
        return {"emails": [], "url": None}
