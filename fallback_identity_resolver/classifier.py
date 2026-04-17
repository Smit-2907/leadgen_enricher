"""
Link Classifier — categorizes raw URLs into platform groups.

Categories: instagram, facebook, linkedin, directory, other

Country-specific directory domains get boosted in the matcher.
No imports from existing pipeline.
"""
import re
from typing import List
from fallback_identity_resolver.models import FallbackCandidate, FallbackCountry

_PLATFORM_RULES = [
    ("instagram", ["instagram.com"]),
    ("facebook",  ["facebook.com", "fb.com"]),
    ("linkedin",  ["linkedin.com"]),
]

_DIRECTORY_DOMAINS: dict[FallbackCountry, list[str]] = {
    "india":     ["justdial.com", "sulekha.com", "indiamart.com", "tradeindia.com"],
    "usa":       ["yelp.com", "yellowpages.com", "manta.com", "bbb.org"],
    "uk":        ["yell.com", "cylex.co.uk", "thomsonlocal.com"],
    "australia": ["yellowpages.com.au", "truelocal.com.au", "hotfrog.com.au"],
    "unknown":   ["yelp.com", "yellowpages.com"],
}

# Flat set of ALL directory domains for quick membership test
_ALL_DIRS = set()
for _v in _DIRECTORY_DOMAINS.values():
    _ALL_DIRS.update(_v)


def classify_candidates(
    candidates: List[FallbackCandidate],
    country: FallbackCountry = "unknown",
) -> List[FallbackCandidate]:
    """
    Mutates each candidate's `category` and `source_weight` in-place.
    Returns the same list for chaining.
    """
    priority_dirs = set(_DIRECTORY_DOMAINS.get(country, []))

    for c in candidates:
        url_low = c.url.lower()
        classified = False

        # Social platforms
        for platform, domains in _PLATFORM_RULES:
            if any(d in url_low for d in domains):
                c.category = platform
                c.source_weight = {
                    "instagram": 0.7,
                    "facebook": 0.8,
                    "linkedin": 0.9,
                }[platform]
                classified = True
                break

        if classified:
            continue

        # Directory check
        if any(d in url_low for d in _ALL_DIRS):
            c.category = "directory"
            # Higher weight for country-priority directories
            c.source_weight = 1.0 if any(d in url_low for d in priority_dirs) else 0.85
            continue

        # Everything else
        c.category = "other"
        c.source_weight = 0.5

    return candidates
