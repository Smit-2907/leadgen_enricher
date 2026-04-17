"""
Core data models for the Global Identity Resolution Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal

Country = Literal["india", "usa", "uk", "australia", "unknown"]

@dataclass
class BusinessInput:
    business_name: str
    city: str
    country: Country = "unknown"
    phone: Optional[str] = None
    website: Optional[str] = None

    def clean_name(self) -> str:
        """Strip legal suffixes for search."""
        import re
        name = self.business_name.lower()
        # Strip bold/decorative unicode characters
        name = re.sub(r'[^\x00-\x7F]+', ' ', name)
        name = re.sub(r'\|\|.*', '', name)  # remove pipe-separated suffixes
        suffixes = [' llp', ' pvt ltd', ' private limited', ' inc.', ' inc',
                    ' corp', ' co.', ' ltd', ' limited', ' b.v.']
        for s in suffixes:
            name = name.replace(s, '')
        return name.strip().title()

    def short_name(self) -> str:
        """First 3 words of clean name."""
        return ' '.join(self.clean_name().split()[:3])


@dataclass
class DiscoveredURL:
    url: str
    source: str
    snippet: str = ""
    confidence: float = 0.0
    platform: Optional[str] = None  # instagram, facebook, etc.


@dataclass
class SocialProfile:
    platform: str
    url: str
    email: Optional[str] = None
    confidence: float = 0.0
    match_reason: str = ""


@dataclass
class EnrichmentOutput:
    business_name: str
    city: str
    emails: List[str] = field(default_factory=list)
    socials: Dict[str, Optional[str]] = field(default_factory=lambda: {
        "instagram": None,
        "facebook": None,
        "linkedin": None,
        "youtube": None,
        "twitter": None,
        "pinterest": None,
    })
    directories: List[str] = field(default_factory=list)
    best_contact_method: str = "phone"
    confidence: Dict[str, float] = field(default_factory=dict)
    reasoning: str = "No digital presence found — phone outreach recommended"
    sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "emails": self.emails,
            "socials": self.socials,
            "directories": self.directories,
            "best_contact_method": self.best_contact_method,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "sources_used": self.sources_used,
        }
