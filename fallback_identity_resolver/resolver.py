"""
fallback_identity_resolver — Main Resolver
==========================================

Entry point: resolve_missing_identity(business_name, city, country)

⚠️  GATE CHECK — This function EXITS immediately if:
      • website is not None
      • phone is not None
    Call it ONLY when both are missing.

Internally isolated — zero imports from pipelines/, search/, match/, extractors/.
"""
import asyncio
import time
from typing import Optional

from fallback_identity_resolver.models import FallbackResult, FallbackCandidate
from fallback_identity_resolver.searcher import run_fallback_search, extract_emails_from_text
from fallback_identity_resolver.classifier import classify_candidates
from fallback_identity_resolver.matcher import rank_candidates
from fallback_identity_resolver.extractor import extract_from_candidate
from fallback_identity_resolver.email_guesser import guess_emails_from_domain


# ─── Gate Check ───────────────────────────────────────────────────────────────

def _gate_check(website: Optional[str], phone: Optional[str]) -> bool:
    """Returns True only when BOTH website and phone are missing."""
    return (website is None or website.strip() == "") \
        and (phone is None or phone.strip() == "")


# ─── Main Entry Point ─────────────────────────────────────────────────────────

async def resolve_missing_identity(
    business_name: str,
    city: str,
    country: str = "unknown",
    *,
    # These are ONLY used for the gate check — not for enrichment
    _website: Optional[str] = None,
    _phone: Optional[str] = None,
) -> Optional[FallbackResult]:
    """
    Fallback identity resolver.

    Returns FallbackResult if something is found.
    Returns None immediately if website OR phone already exists (gate check).

    Parameters
    ----------
    business_name : str
    city          : str
    country       : "india" | "usa" | "uk" | "australia" | "unknown"
    _website      : Pass the existing website value for the gate check.
    _phone        : Pass the existing phone value for the gate check.
    """
    # ── GATE: exit if we already have a phone or website ──────────────────────
    if not _gate_check(_website, _phone):
        return None  # Existing pipeline handles this — do nothing.

    start = time.time()
    result = FallbackResult()
    result.sources_checked = []

    # ─ STEP 1: Run parallel search queries ────────────────────────────────────
    candidates = await run_fallback_search(business_name, city)
    result.sources_checked.append(f"search:{len(candidates)}_urls")

    # ─ STEP 2: Quick email harvest from snippets (zero-cost) ──────────────────
    for c in candidates:
        snippet_emails = extract_emails_from_text(c.snippet)
        for e in snippet_emails:
            if e not in result.emails:
                result.emails.append(e)
    if result.emails:
        result.sources_checked.append("snippet_extraction")

    # ─ STEP 3: Classify links by platform + country priority ──────────────────
    candidates = classify_candidates(candidates, country=country)  # type: ignore

    # ─ STEP 4: Score & filter via entity matching engine ──────────────────────
    accepted = rank_candidates(candidates, business_name, city)
    result.sources_checked.append(f"matched:{len(accepted)}_accepted")

    if not accepted and not result.emails:
        # Nothing matched — return graceful fallback message
        result.message = "No online presence found beyond Google Maps."
        result.best_contact_method = "manual"
        result.sources_checked.append(f"completed_in_{round(time.time()-start,2)}s")
        return result

    # ─ STEP 5: Classify accepted candidates by platform ───────────────────────
    instagram_urls = [c for c in accepted if c.category == "instagram"]
    facebook_urls  = [c for c in accepted if c.category == "facebook"]
    linkedin_urls  = [c for c in accepted if c.category == "linkedin"]
    directory_urls = [c for c in accepted if c.category == "directory"]
    other_urls     = [c for c in accepted if c.category == "other"]

    # ─ STEP 6: Run all extractors in parallel with per-task timeouts ──────────
    extract_tasks = {}

    def _add(key: str, candidates_list: list):
        if candidates_list:
            best = candidates_list[0]  # highest confidence
            extract_tasks[key] = extract_from_candidate(best.category, best.url)

    _add("instagram", instagram_urls)
    _add("facebook",  facebook_urls)
    _add("linkedin",  linkedin_urls)
    _add("directory", directory_urls)
    _add("other",     other_urls)

    if extract_tasks:
        keys = list(extract_tasks.keys())
        raw_results = await asyncio.gather(*extract_tasks.values(), return_exceptions=True)

        for key, raw in zip(keys, raw_results):
            if isinstance(raw, Exception) or not isinstance(raw, dict):
                continue

            # Collect emails
            for e in raw.get("emails", []):
                if e not in result.emails:
                    result.emails.append(e)

            # Record social profiles
            if key in result.socials and raw.get("url"):
                result.socials[key] = raw["url"]

            # Record directory URL
            if key == "directory" and raw.get("url"):
                result.directories.append(raw["url"])

        result.sources_checked.append("platform_extraction")

    # ─ STEP 7: Email guessing from domain (safe, last resort) ─────────────────
    # Find a non-social domain URL in accepted candidates
    if not result.emails:
        candidate_with_domain = next(
            (c for c in accepted if c.category in ("directory", "other")
             and c.url.startswith("http")),
            None
        )
        if candidate_with_domain:
            guessed = await guess_emails_from_domain(candidate_with_domain.url)
            if guessed:
                result.emails.extend(guessed[:3])
                result.sources_checked.append("email_guesser")

    # ─ STEP 8: Finalize output ────────────────────────────────────────────────
    result.emails = sorted(set(result.emails))

    # Compute overall confidence score (max of all accepted candidates)
    result.confidence_score = round(
        max((c.confidence for c in accepted), default=0.0), 3
    )

    # Determine best contact method
    if result.emails:
        result.best_contact_method = "email"
        scraped_emails = [e for e in result.emails if "@" in e and "." in e.split("@")[1]]
        result.message = f"Found {len(scraped_emails)} email(s) via fallback identity resolution."
    elif any(v for v in result.socials.values()):
        result.best_contact_method = "social"
        active = [k for k, v in result.socials.items() if v]
        result.message = f"Found social profiles via fallback: {', '.join(active)}."
    else:
        result.best_contact_method = "manual"
        result.message = "No online presence found beyond Google Maps."

    elapsed = round(time.time() - start, 2)
    result.sources_checked.append(f"completed_in_{elapsed}s")

    return result
