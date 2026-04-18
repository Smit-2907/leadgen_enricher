"""
Main Pipeline — resolve_identity()

This is the single integration point.
Call with a BusinessInput, get back an EnrichmentOutput.

Execution flow:
  1. Check cache
  2. Detect country
  3. Run search queries in parallel
  4. Score & rank results
  5. Extract emails from snippets (zero-cost, instant)
  6. Scrape website if provided
  7. Scrape top social profiles for emails
  8. Guess emails from domain if none found
  9. Finalize output with confidence + reasoning
 10. Cache and return
"""
import asyncio
import time
from typing import Optional
from search.models import BusinessInput, EnrichmentOutput, DiscoveredURL
from search.country_detector import detect_country
from search.query_builder import run_all_queries, PLATFORM_DOMAINS
from match.entity_matcher import rank_and_filter
from extractors.snippet_extractor import extract_emails_from_snippets
from extractors.website_extractor import scrape_website
from extractors.social_extractor import scrape_social_bio
from extractors.email_guesser import guess_emails
from search.utils import is_noise_url, extract_emails
import cache.store as cache_store


async def resolve_identity(
    business_name: str,
    city: str,
    country: str = "unknown",
    phone: Optional[str] = None,
    website: Optional[str] = None,
) -> EnrichmentOutput:
    """
    Main entrypoint. Returns structured EnrichmentOutput.
    Target: <5s per lead.
    """
    start = time.time()

    # 1. Cache check
    cached = cache_store.get(business_name, city)
    if cached:
        cached.sources_used.insert(0, "cache")
        return cached

    # 2. Build input model + detect country
    if country == "unknown":
        country = detect_country(city, phone)

    biz = BusinessInput(
        business_name=business_name,
        city=city,
        country=country,  # type: ignore
        phone=phone,
        website=website,
    )

    output = EnrichmentOutput(business_name=business_name, city=city)
    sources_used = []

    # 3. Run all search queries in parallel
    raw_urls = await run_all_queries(biz)
    sources_used.append("search_engine")

    # 4. Score & rank
    ranked = rank_and_filter(raw_urls, biz, threshold=0.12)

    # 5. Extract emails from snippets instantly (NO network calls)
    snippet_emails = extract_emails_from_snippets(raw_urls)
    if snippet_emails:
        output.emails.extend(snippet_emails)
        sources_used.append("snippet_extraction")

    # Also scan ALL snippets regardless of score (might catch phone-matched business)
    all_snippet_emails = extract_emails_from_snippets(raw_urls)
    for e in all_snippet_emails:
        if e not in output.emails:
            output.emails.append(e)

    # 6. Classify social URLs from ranked results
    social_urls: dict[str, Optional[str]] = {p: None for p in PLATFORM_DOMAINS}
    directory_urls = []
    discovered_website = None

    # Get known directory domains for the country to avoid treating them as the "Official Website"
    directories_to_skip = [
        "yelp.", "justdial.", "yellowpages.", "facebook.", "instagram.", "linkedin.", 
        "twitter.", "youtube.", "indiamart.", "sulekha.", "manta.", "tradeindia.",
        "cybo.", "worldorgs.", "lentlo.", "asklaila.", "local.google.", "mapping.",
        "tripadvisor.", "crunchbase.", "glassdoor.", "zoominfo.", "apollo.io"
    ]

    for r in ranked:
        url_lower = r.url.lower()
        placed_as_social = False
        
        # 6a. Try to place as a social platform
        for platform, domain in PLATFORM_DOMAINS.items():
            if domain in url_lower and not is_noise_url(r.url):
                if social_urls[platform] is None:
                    social_urls[platform] = r.url
                    placed_as_social = True
                    break
        
        if placed_as_social:
            continue

        # 6b. Try to identify as an "Official Website" candidate
        # It must have high confidence and not be a known directory or social network
        if not discovered_website and r.confidence >= 0.25:
             is_directory = any(d in url_lower for d in directories_to_skip)
             if not is_directory:
                 discovered_website = r.url

        # 6c. Place as a directory result
        if r.confidence >= 0.15:
            directory_urls.append(r.url)

    output.socials = social_urls
    output.directories = directory_urls[:5]
    if directory_urls:
        sources_used.append("directories")

    # 7. Scrape website in parallel with top social profiles
    # If the user didn't provide a website, but we found one that looks like an official site, use it!
    target_website = website or discovered_website
    
    tasks_meta = []
    coros = []
    
    if target_website:
        if not website:
            sources_used.append("website_discovery")
        tasks_meta.append("website")
        coros.append(asyncio.wait_for(scrape_website(target_website), timeout=20.0))
    for platform, url in social_urls.items():
        if url:
            tasks_meta.append(f"social:{platform}")
            coros.append(asyncio.wait_for(scrape_social_bio(url, platform), timeout=12.0))

    if coros:
        results = await asyncio.gather(*coros, return_exceptions=True)
        for label, result in zip(tasks_meta, results):
            if isinstance(result, Exception):
                continue
            if label == "website" and isinstance(result, dict):
                for e in result.get("emails", []):
                    if e not in output.emails:
                        output.emails.append(e)
                for platform, url in result.get("socials", {}).items():
                    if url and output.socials.get(platform) is None:
                        output.socials[platform] = url
                if result.get("emails"):
                    sources_used.append("website_scrape")
            elif label.startswith("social:") and isinstance(result, str):
                if result and result not in output.emails:
                    output.emails.append(result)
                    sources_used.append(f"bio_scrape:{label.split(':')[1]}")

    # 8. Email guessing from domain (last resort)
    if not output.emails and target_website:
        guessed = await guess_emails(target_website)
        if guessed:
            output.emails = guessed[:3]  # top 3 guesses
            output.confidence["guessed_emails"] = 0.3
            sources_used.append("email_guesser")

    # 8b. NO-WEBSITE ENRICHMENT SERVICE
    if not output.emails and website is None:
        from pipelines.no_website_enrichment import no_website_enrichment as run_enrichment
        enrich_res = await run_enrichment(business_name, city, phone)
        if enrich_res.get("emails"):
            # Take best result for main email, store others
            top_emails = [e["value"] for e in enrich_res["emails"]]
            output.emails.extend(top_emails)
            output.confidence["no_website_enrichment"] = enrich_res.get("confidence_score", 0.0)
            sources_used.append("no_website_enrichment")
            
            # Map socials if found
            for s in enrich_res.get("socials", []):
                if output.socials.get(s["platform"]) is None:
                    output.socials[s["platform"]] = s["url"]

    # 9. Finalize reasoning & confidence
    output.emails = sorted(set(output.emails))
    output.sources_used = list(dict.fromkeys(sources_used))  # unique, preserve order

    # Compute per-source confidence
    reasons = []
    if output.emails:
        output.confidence["email"] = 0.90 if "website_scrape" in sources_used else 0.70
        output.best_contact_method = "email"
        reasons.append(f"Email found via {', '.join(sources_used[:2])}")
    elif any(v for v in output.socials.values()):
        output.confidence["social"] = 0.75
        output.best_contact_method = "social"
        active = [p for p, v in output.socials.items() if v]
        reasons.append(f"Social profiles found: {', '.join(active)}")
    else:
        output.best_contact_method = "phone"
        reasons.append("No digital presence found — phone outreach recommended")

    if phone and any("phone" in s for s in sources_used):
        output.confidence["phone_verified"] = 0.85
        reasons.append("Phone number cross-referenced in listings")

    output.reasoning = " | ".join(reasons)

    elapsed = round(time.time() - start, 2)
    output.sources_used.append(f"completed_in_{elapsed}s")

    # 10. Cache result
    cache_store.set(business_name, city, output)

    return output
