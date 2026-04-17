from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class LeadIn(BaseModel):
    """Initial lead data from the existing scraper."""
    business_name: str
    location: str
    phone: Optional[str] = None
    website: Optional[str] = None

class SocialProfile(BaseModel):
    """A found social media profile."""
    platform: str  # Instagram, Facebook, LinkedIn, etc.
    url: HttpUrl
    name_on_platform: Optional[str] = None
    confidence_score: float = 0.0

class EnrichmentResult(BaseModel):
    """Full enriched lead data."""
    business_name: str
    location: str
    phone: Optional[str] = None
    website: Optional[str] = None
    social_profiles: List[SocialProfile] = []
    emails: List[str] = []
    sources: List[str] = []

    class Config:
        arbitrary_types_allowed = True
