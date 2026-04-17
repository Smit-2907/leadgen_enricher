"""
Website Extractor — scrapes a business website for emails + social links.
Tries fast HTTP first. If site uses JS, falls back to Playwright.
"""
import asyncio
import re
from typing import List, Dict, Optional, Set
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from search.utils import random_ua, jitter, extract_emails, is_noise_url

SOCIAL_PATTERNS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "twitter": "twitter.com",
    "pinterest": "pinterest.com",
}
CONTACT_KEYWORDS = re.compile(r'contact|about|reach|connect|enquir', re.IGNORECASE)


async def _http_scrape(url: str, client: httpx.AsyncClient) -> str:
    resp = await client.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.text


async def _playwright_scrape(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=random_ua())
            await Stealth().apply_stealth_async(page)
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
            return await page.content()
        finally:
            await browser.close()


def _extract_socials_from_html(html: str, base_url: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    socials: Dict[str, Optional[str]] = {k: None for k in SOCIAL_PATTERNS}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if is_noise_url(href):
            continue
        for platform, domain in SOCIAL_PATTERNS.items():
            if domain in href and socials[platform] is None:
                socials[platform] = a["href"]
    return socials


def _find_contact_subpages(html: str, base_domain: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    pages = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if CONTACT_KEYWORDS.search(href) or CONTACT_KEYWORDS.search(a.get_text()):
            if href.startswith("/"):
                pages.append(f"https://{base_domain}{href}")
            elif href.startswith("http") and base_domain in href:
                pages.append(href)
    return list(set(pages[:3]))


async def scrape_website(url: str) -> Dict:
    """Returns dict with emails[], socials{}. Uses fast path then Playwright fallback."""
    if not url:
        return {"emails": [], "socials": {}}
    if not url.startswith("http"):
        url = f"https://{url}"

    emails: Set[str] = set()
    socials: Dict[str, Optional[str]] = {k: None for k in SOCIAL_PATTERNS}

    base_domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]

    async with httpx.AsyncClient(headers={"User-Agent": random_ua()}, follow_redirects=True) as client:
        html = ""
        # Plan A: Fast HTTP
        try:
            html = await _http_scrape(url, client)
        except Exception:
            pass

        # Plan B: Playwright if empty or no emails
        if not html or not extract_emails(html):
            try:
                html = await _playwright_scrape(url)
            except Exception:
                pass

        if html:
            emails.update(extract_emails(html))
            socials.update(_extract_socials_from_html(html, base_domain))

            # Crawl contact subpages if still no email
            if not emails:
                subpages = _find_contact_subpages(html, base_domain)
                for sp in subpages:
                    try:
                        sub_html = await _http_scrape(sp, client)
                        emails.update(extract_emails(sub_html))
                        socials.update({k: v for k, v in _extract_socials_from_html(sub_html, base_domain).items() if v})
                    except Exception:
                        pass

    return {"emails": sorted(emails), "socials": socials}
