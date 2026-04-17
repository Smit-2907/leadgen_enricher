"""
Fallback Models — completely self-contained data structures.
No imports from search/, match/, extractors/, or pipelines/.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal

FallbackCountry = Literal["india", "usa", "uk", "australia", "unknown"]


@dataclass
class FallbackCandidate:
    """A single URL discovered during fallback search."""
    url: str
    title: str = ""
    snippet: str = ""
    category: str = "other"      # instagram | facebook | linkedin | directory | other
    name_similarity: float = 0.0
    city_match: bool = False
    source_weight: float = 0.5
    confidence: float = 0.0


@dataclass
class FallbackResult:
    """Final output from the fallback identity resolver."""
    emails: List[str] = field(default_factory=list)
    socials: Dict[str, Optional[str]] = field(default_factory=lambda: {
        "instagram": None,
        "facebook": None,
        "linkedin": None,
    })
    directories: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    best_contact_method: str = "manual"   # social | email | manual
    message: str = "No online presence found beyond Google Maps."
    sources_checked: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "emails": self.emails,
            "socials": {k: v for k, v in self.socials.items() if v},
            "directories": self.directories,
            "confidence_score": self.confidence_score,
            "best_contact_method": self.best_contact_method,
            "message": self.message,
        }
