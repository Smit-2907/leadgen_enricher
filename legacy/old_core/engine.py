import asyncio
import re
from typing import List, Set
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from core.models import LeadIn, EnrichmentResult, SocialProfile
from scrapers.search_engines import SearchEngineScraper
from scrapers.email_finder import EmailFinder
from scrapers.social_platforms import SocialPlatformScraper
from scrapers.directories import DirectoryScraper
from scrapers.whois_lookup import WhoisLookup
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.phone_lookup import PhoneLookup
from scrapers.indiamart_scraper import IndiaMartScraper
from scrapers.justdial_decoder import JustDialDecoder
from scrapers.truecaller_lookup import TruecallerLookup
from scrapers.directory_sniffer import DirectorySniffer
from core.utils import is_valid_match, retry_async, get_random_user_agent, EMAIL_REGEX, clean_business_name

class EnrichmentEngine:
    def __init__(self):
        self.searcher = SearchEngineScraper()
        self.email_finder = EmailFinder()
        self.social_scraper = SocialPlatformScraper()
        self.dir_scraper = DirectoryScraper()
        self.whois = WhoisLookup()
        self.youtube = YouTubeScraper()
        self.phone_lookup = PhoneLookup()
        self.indiamart = IndiaMartScraper()
        self.jd_decoder = JustDialDecoder()
        self.truecaller = TruecallerLookup()
        self.sniffer = DirectorySniffer()

    @retry_async(retries=2, delay=2)
    async def enrich_lead(self, lead: LeadIn) -> EnrichmentResult:
        """The absolute final bullet-proof enrichment pipeline."""
        result = EnrichmentResult(
            business_name=lead.business_name,
            location=lead.location,
            phone=lead.phone,
            website=lead.website
        )
        seen_urls: Set[str] = set()

        # STEP 1: Parallel Core Search (Socials & Website Emails)
        tasks = [self.searcher.find_social_urls(lead.business_name, lead.location)]
        if lead.website:
            tasks.append(self.email_finder.find_emails_from_url(lead.website))
        else:
            tasks.append(asyncio.sleep(0, result=[]))
        
        social_profiles, website_emails = await asyncio.gather(*tasks)
        
        # Filtering with keyword allowance (Resilient Naming)
        clean_name = clean_business_name(lead.business_name)
        biz_keywords = [k for k in clean_name.lower().split() if len(k) > 2]
        
        for p in social_profiles:
            url_str = str(p.url).lower().rstrip('/')
            if url_str in seen_urls: continue
            
            # Avoid noisy URLs like tags, single posts, or reels
            noise_markers = ['explore/tags', '/p/', '/reel/', '/events/', '/groups/', 'status/']
            if any(marker in url_str for marker in noise_markers):
                continue
            
            is_valid = is_valid_match(lead.business_name, p.name_on_platform or "") or \
                       is_valid_match(clean_name, p.name_on_platform or "") or \
                       any(kw in url_str for kw in biz_keywords)
            
            if is_valid:
                result.social_profiles.append(p)
                seen_urls.add(url_str)

        result.emails.extend(website_emails)

        # STEP 2: Website -> Social Extraction (Deep Scrape)
        if lead.website and not result.social_profiles:
            found_socials = await self._find_socials_on_website(lead.website)
            for s in found_socials:
                if s.url not in seen_urls:
                    result.social_profiles.append(s)
                    seen_urls.add(str(s.url))

        # STEP 3: Last Resort Email Discovery (WHOIS, IndiaMART, YouTube)
        if not result.emails:
            fallbacks = [self.youtube.find_channel_and_email(lead.business_name, lead.location)]
            if lead.website:
                fallbacks.append(self.whois.get_registrant_email(lead.website))
            fallbacks.append(self.indiamart.find_contact_info(lead.business_name, lead.location))
            
            fallback_results = await asyncio.gather(*fallbacks)
            for res in fallback_results:
                if isinstance(res, list): result.emails.extend(res)
                elif res: result.emails.append(res)

        # STEP 4: Deep Directory Intel (JustDial Decoder & Truecaller)
        if not result.phone and any(x in lead.location.lower() for x in ['india', 'pune', 'kolkata', 'mumbai']):
            jd_phone = await self.jd_decoder.get_decoded_phone(f"https://www.justdial.com/{lead.location}/{lead.business_name}")
            if jd_phone: result.phone = jd_phone

        if result.phone and not result.business_name:
            tc_name = await self.truecaller.reverse_phone_search(result.phone)
            # if tc_name: result.meta['truecaller_name'] = tc_name

        # STEP 5: Social Bio Final Cleanup
        if not result.emails and result.social_profiles:
            for profile in result.social_profiles[:3]:
                social_email = await self.social_scraper.scrape_bio(str(profile.url))
                if social_email and social_email not in result.emails:
                    result.emails.append(social_email)

        # STEP 6: Deep Web Snippet Dorking & Directory Sniffing
        if not result.emails:
            # Parallelize the last resort
            dork_results = await asyncio.gather(
                self.searcher.find_emails_via_dork(lead.business_name, lead.location, result.phone),
                self.sniffer.hunt_emails(lead.business_name, lead.location)
            )
            for emails in dork_results:
                if emails: result.emails.extend(emails)

        result.emails = list(set([e.lower() for e in result.emails if "@" in e]))
        result.sources = ["Search", "DeepWeb", "WHOIS", "IndiaMART", "YouTube", "Truecaller", "Dorking", "Directories"]
        return result

    async def _find_socials_on_website(self, url: str) -> List[SocialProfile]:
        """Deep dive into website with Playwright to find social links."""
        found = []
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=get_random_user_agent())
                await Stealth().apply_stealth_async(page)
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Mimic human behavior to trigger lazy-loaded footers/headers
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(5) 
                
                # Look for all likely social links
                links = await page.query_selector_all("a[href*='facebook.com'], a[href*='instagram.com'], a[href*='linkedin.com']")
                noise_markers = ['explore/tags', '/p/', '/reel/', '/events/', '/groups/', 'status/', 'share']
                for l in links:
                    href = await l.get_attribute("href")
                    if href:
                        href_lower = href.lower()
                        if any(marker in href_lower for marker in noise_markers):
                            continue
                        platform = "facebook" if "facebook" in href_lower else "instagram" if "instagram" in href_lower else "linkedin"
                        # Extra uniqueness check
                        if not any(f.url == href for f in found):
                            found.append(SocialProfile(platform=platform, url=href, confidence_score=0.9))
            except: pass
            finally: await browser.close()
        return found

    async def shutdown(self):
        await self.email_finder.close()
        await self.dir_scraper.close()
