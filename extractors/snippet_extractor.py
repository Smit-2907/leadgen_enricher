"""
Snippet Email Extractor — extracts emails directly from search result snippets.
Zero HTTP calls needed, ultra-fast.
"""
from typing import List
from search.models import DiscoveredURL
from search.utils import extract_emails


def extract_emails_from_snippets(urls: List[DiscoveredURL]) -> List[str]:
    """Scan all search result snippets for emails — no network calls."""
    emails = set()
    for r in urls:
        found = extract_emails(r.snippet)
        emails.update(found)
    return sorted(emails)
