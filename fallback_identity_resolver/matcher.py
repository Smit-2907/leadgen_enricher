"""
Entity Matcher — scores each FallbackCandidate against the input business.

Confidence formula (exact spec):
  confidence = (name_similarity * 0.5) + (city_match * 0.3) + (source_weight * 0.2)

Filter rules:
  REJECT if name_similarity < 0.6
  REJECT if city does not appear in title/snippet
  ACCEPT if confidence >= 0.7

No imports from existing pipeline.
"""
import re
from typing import List
from rapidfuzz import fuzz
from fallback_identity_resolver.models import FallbackCandidate

_THRESHOLD_NAME_SIM = 0.6
_THRESHOLD_CONFIDENCE = 0.7


def _name_similarity(business_name: str, text: str) -> float:
    """Partial ratio between business name and title/snippet text."""
    if not business_name or not text:
        return 0.0
    return fuzz.partial_ratio(business_name.lower(), text.lower()) / 100.0


def _city_match(city: str, text: str) -> bool:
    """True if any word from city appears in the combined candidate text."""
    city_words = set(re.findall(r'\w+', city.lower()))
    text_low = text.lower()
    return any(w in text_low for w in city_words if len(w) > 2)


def score_candidate(
    candidate: FallbackCandidate,
    business_name: str,
    city: str,
) -> FallbackCandidate:
    """
    Compute and store confidence score in-place.
    Returns the candidate for chaining.
    """
    combined_text = f"{candidate.title} {candidate.snippet} {candidate.url}"

    # Name similarity against title + snippet
    name_sim = _name_similarity(business_name, combined_text)
    city_ok = _city_match(city, combined_text)

    candidate.name_similarity = round(name_sim, 3)
    candidate.city_match = city_ok

    # Exact confidence formula from spec
    candidate.confidence = round(
        (name_sim * 0.5)
        + (float(city_ok) * 0.3)
        + (candidate.source_weight * 0.2),
        3,
    )
    return candidate


def rank_candidates(
    candidates: List[FallbackCandidate],
    business_name: str,
    city: str,
) -> List[FallbackCandidate]:
    """
    Score all candidates, filter by spec rules, sort by confidence descending.
    Returns only accepted candidates (confidence >= 0.7, name_sim >= 0.6, city matches).
    """
    scored = [score_candidate(c, business_name, city) for c in candidates]

    accepted = [
        c for c in scored
        if c.name_similarity >= _THRESHOLD_NAME_SIM
        and c.city_match
        and c.confidence >= _THRESHOLD_CONFIDENCE
    ]

    accepted.sort(key=lambda c: c.confidence, reverse=True)
    return accepted
