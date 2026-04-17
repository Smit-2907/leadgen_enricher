"""
Entity Matching Engine — scores discovered URLs against the input business.
Uses rapidfuzz for fuzzy name matching plus structural signals.
"""
import re
from typing import List, Tuple
from rapidfuzz import fuzz
from search.models import BusinessInput, DiscoveredURL
from search.utils import get_domain, is_noise_url

PLATFORM_DOMAINS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "twitter": "twitter.com",
    "pinterest": "pinterest.com",
}

SCORE_WEIGHTS = {
    "phone_match": 0.40,
    "name_in_url": 0.25,
    "name_title_sim": 0.20,
    "city_match": 0.10,
    "domain_match": 0.05,
}


def _slug_overlap(name: str, url: str) -> float:
    """Check if name keywords appear in the URL path."""
    slug = re.sub(r'[^a-z0-9]', '', name.lower())
    url_clean = re.sub(r'[^a-z0-9]', '', url.lower())
    if not slug:
        return 0.0
    # Check if 2+ consecutive chars from slug appear in url
    matches = sum(1 for ch in slug if ch in url_clean)
    return min(matches / len(slug), 1.0)


def _name_similarity(name: str, title: str) -> float:
    if not name or not title:
        return 0.0
    return fuzz.partial_ratio(name.lower(), title.lower()) / 100.0


def _phone_in_text(phone: str, text: str) -> bool:
    if not phone:
        return False
    digits = re.sub(r"\D", "", phone)[-10:]  # last 10 digits
    return digits in re.sub(r"\D", "", text)


def score_url(url_result: DiscoveredURL, biz: BusinessInput) -> Tuple[DiscoveredURL, float]:
    """Compute a 0-1 confidence score for a URL against a business input."""
    if is_noise_url(url_result.url):
        url_result.confidence = 0.0
        return url_result, 0.0

    # Platform domain lock — reject cross-contamination
    if url_result.platform:
        expected_domain = PLATFORM_DOMAINS.get(url_result.platform, "")
        if expected_domain and expected_domain not in url_result.url.lower():
            url_result.confidence = 0.0
            return url_result, 0.0

    combined_text = f"{url_result.url} {url_result.snippet}"
    cn = biz.clean_name()
    sn = biz.short_name()

    score = 0.0

    # Phone match (strongest signal)
    if biz.phone and _phone_in_text(biz.phone, combined_text):
        score += SCORE_WEIGHTS["phone_match"]

    # Name in URL slug
    url_slug_score = max(_slug_overlap(cn, url_result.url), _slug_overlap(sn, url_result.url))
    score += SCORE_WEIGHTS["name_in_url"] * url_slug_score

    # Name similarity with snippet title
    title_score = max(_name_similarity(cn, combined_text[:200]), _name_similarity(sn, combined_text[:200]))
    score += SCORE_WEIGHTS["name_title_sim"] * title_score

    # City in snippet
    if biz.city.lower() in combined_text.lower():
        score += SCORE_WEIGHTS["city_match"]

    # Website/domain match
    if biz.website and get_domain(biz.website) in get_domain(url_result.url):
        score += SCORE_WEIGHTS["domain_match"]

    url_result.confidence = round(min(score, 1.0), 3)
    return url_result, url_result.confidence


def rank_and_filter(candidates: List[DiscoveredURL], biz: BusinessInput, threshold: float = 0.15) -> List[DiscoveredURL]:
    """Score all candidates, filter by threshold, return sorted."""
    scored = [score_url(c, biz) for c in candidates]
    filtered = [(r, s) for r, s in scored if s >= threshold]
    filtered.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in filtered]
