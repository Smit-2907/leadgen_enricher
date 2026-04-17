import asyncio
from typing import List
from core.models import LeadIn, EnrichmentResult, SocialProfile
from scrapers.search_engines import SearchEngineScraper
from scrapers.email_finder import EmailFinder
from scrapers.social_platforms import SocialPlatformScraper
from scrapers.directories import DirectoryScraper
from scrapers.whois_lookup import WhoisLookup
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.phone_lookup import PhoneLookup
from core.utils import is_valid_match, retry_async

class EnrichmentEngine:
    def __init__(self):
        self.searcher = SearchEngineScraper()
        self.email_finder = EmailFinder()
        self.social_scraper = SocialPlatformScraper()
        self.dir_scraper = DirectoryScraper()
        self.whois = WhoisLookup()
        self.youtube = YouTubeScraper()
        self.phone_lookup = PhoneLookup()

    @retry_async(retries=2, delay=2)
    async def enrich_lead(self, lead: LeadIn) -> EnrichmentResult:
        """The bullet-proof enrichment pipeline with multi-level fallbacks."""
        result = EnrichmentResult(
            business_name=lead.business_name,
            location=lead.location,
            phone=lead.phone,
            website=lead.website
        )

        # Level 1: Primary Search (Socials & Website Emails)
        tasks = [
            self.searcher.find_social_urls(lead.business_name, lead.location),
        ]
        if lead.website:
            tasks.append(self.email_finder.find_emails_from_url(lead.website))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        social_profiles, website_emails = await asyncio.gather(*tasks)
        
        # Apply strict naming filter
        seen_urls = set()
        for p in social_profiles:
            url_str = str(p.url).lower().rstrip('/')
            if is_valid_match(lead.business_name, p.name_on_platform or ""):
                result.social_profiles.append(p)
                seen_urls.add(url_str)

        result.emails.extend(website_emails)

        # Level 2: Phone Reverse Lookup (Socials)
        if lead.phone and len(result.social_profiles) < 2:
            phone_links = await self.phone_lookup.reverse_search(lead.phone)
            for link in phone_links:
                if link.lower().rstrip('/') not in seen_urls:
                    result.social_profiles.append(SocialProfile(
                        platform="phone_match", url=link
                    ))
                    seen_urls.add(link.lower().rstrip('/'))

        # Level 3: Secondary Directories (India Focus)
        if len(result.social_profiles) < 2:
            if any(x in lead.location.lower() for x in ['india', 'pune', 'mumbai', 'delhi', 'bangalore']):
                dir_links = await self.dir_scraper.search_justdial(lead.business_name, lead.location)
                for link in dir_links:
                    if link.lower().rstrip('/') not in seen_urls:
                        result.social_profiles.append(SocialProfile(
                            platform="directory", url=link
                        ))
                        seen_urls.add(link.lower().rstrip('/'))

        # Level 4: "Last Resort" Email Discovery (WHOIS & YouTube)
        if not result.emails:
            last_resort_tasks = []
            if lead.website:
                last_resort_tasks.append(self.whois.get_registrant_email(lead.website))
            
            last_resort_tasks.append(self.youtube.find_channel_and_email(lead.business_name, lead.location))
            
            last_resort_results = await asyncio.gather(*last_resort_tasks)
            for email in last_resort_results:
                if email and email not in result.emails:
                    result.emails.append(email)

        # Level 5: Social Bio Scrape (If still no email)
        if not result.emails and result.social_profiles:
            for profile in result.social_profiles[:2]:
                social_email = await self.social_scraper.scrape_bio(str(profile.url))
                if social_email and social_email not in result.emails:
                    result.emails.append(social_email)

        result.emails = list(set([e.lower() for e in result.emails]))
        result.sources = ["Search", "Website", "Phone", "WHOIS", "YouTube", "SocialBio"]
        
        return result

    async def shutdown(self):
        await self.email_finder.close()
        await self.dir_scraper.close()
