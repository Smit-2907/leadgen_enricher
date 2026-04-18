import asyncio
import re
import dns.resolver
import smtplib
import sqlite3
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright
from duckduckgo_search import DDGS

from search.utils import random_ua, extract_emails, get_domain
from extractors.website_extractor import scrape_website

# DB for isolated storage
DB_PATH = 'enrichment_results.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrichment_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
            location TEXT,
            emails TEXT,
            socials TEXT,
            confidence_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_enrichment(name: str, location: str, result: Dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO enrichment_results (business_name, location, emails, socials, confidence_score)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, location, json.dumps(result['emails']), json.dumps(result['socials']), result['confidence_score']))
    conn.commit()
    conn.close()

class NoWebsiteEnricher:
    def __init__(self, name: str, location: str, phone: Optional[str] = None):
        self.name = name
        self.location = location
        self.phone = phone
        self.emails = [] # List of {value, confidence, source}
        self.socials = [] # List of {platform, url}
        self.sources_checked = []
        
    async def run_search(self, query: str, max_results: int = 5, context=None) -> List[str]:
        urls = []
        # Try API first
        try:
            with DDGS(headers={"User-Agent": random_ua()}) as ddgs:
                results = ddgs.text(query, max_results=max_results)
                for r in results:
                    urls.append(r['href'])
        except Exception:
            pass
        
        # Fallback to Playwright scraping if API fails and context is available
        if not urls and context:
            try:
                page = await context.new_page()
                # Use DuckDuckGo HTML or Lite version which is easier to scrape
                search_url = f"https://duckduckgo.com/lite/?q={query.replace(' ', '+')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                # Select all links that look like external results
                links = await page.query_selector_all("a.result-link")
                for link in links:
                    href = await link.get_attribute("href")
                    if href and href.startswith("http"):
                        urls.append(href)
                        if len(urls) >= max_results:
                            break
                await page.close()
            except Exception:
                pass
                
        return urls

    async def scrape_page(self, url: str, browser_context) -> str:
        try:
            page = await browser_context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(1)
            content = await page.content()
            await page.close()
            return content
        except Exception:
            return ""

    async def validate_email(self, email: str) -> bool:
        # Syntax
        if not re.match(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", email):
            return False
        
        domain = email.split('@')[1]
        try:
            # MX Record
            records = await asyncio.to_thread(dns.resolver.resolve, domain, 'MX')
            if not records:
                return False
            
            # SMTP Probe (best effort)
            # mx = str(records[0].exchange)
            # server = smtplib.SMTP(timeout=3)
            # server.connect(mx)
            # server.helo()
            # server.mail('test@example.com')
            # code, message = server.rcpt(email)
            # server.quit()
            # return code == 250
            return True # Returning True after MX for stability in restricted envs
        except:
            return False

    async def step1_google_search(self, browser_context):
        self.sources_checked.append("search_engine")
        queries = [
            f'"{self.name}" "{self.location}" contact email',
            f'"{self.name}" "{self.location}" business email',
            f'"{self.name}" "{self.location}" @gmail.com',
        ]
        
        all_urls = []
        for q in queries:
            urls = await self.run_search(q, 5, context=browser_context)
            all_urls.extend(urls)
        
        # Parallel scraping with a semaphore to avoid overloading
        sem = asyncio.Semaphore(3)
        async def limited_scrape(url):
            async with sem:
                return await self.scrape_page(url, browser_context)
                
        tasks = [limited_scrape(url) for url in set(all_urls[:10])]
        pages = await asyncio.gather(*tasks)
        
        for html in pages:
            if not html: continue
            found = extract_emails(html)
            for e in found:
                if await self.validate_email(e):
                    self.emails.append({"value": e, "confidence": 0.70, "source": "search_result"})

    async def step2_directory_scraping(self, browser_context):
        # Implementation for JustDial, IndiaMART, Yelp
        self.sources_checked.append("directories")
        queries = [
            f'site:justdial.com "{self.name}" "{self.location}"',
            f'site:indiamart.com "{self.name}" "{self.location}"',
            f'site:yelp.com "{self.name}" "{self.location}"'
        ]
        
        all_urls = []
        for q in queries:
            urls = await self.run_search(q, 2, context=browser_context)
            all_urls.extend(urls)
            
        for url in all_urls:
            html = await self.scrape_page(url, browser_context)
            emails = extract_emails(html)
            for e in emails:
                if await self.validate_email(e):
                    self.emails.append({"value": e, "confidence": 0.80, "source": "directory"})
            
            # Try finding website
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'http' in href and not any(d in href for d in ['justdial', 'yelp', 'facebook', 'google']):
                    # Potential business site
                    site_res = await scrape_website(href)
                    for e in site_res.get('emails', []):
                        if await self.validate_email(e):
                            self.emails.append({"value": e, "confidence": 0.95, "source": "website_direct"})
                    break

    async def step3_facebook_discovery(self, browser_context):
        self.sources_checked.append("facebook")
        q = f'"{self.name}" "{self.location}" facebook'
        urls = await self.run_search(q, 1)
        for url in urls:
            if 'facebook.com' in url:
                self.socials.append({"platform": "facebook", "url": url})
                about_url = url.rstrip('/') + '/about'
                html = await self.scrape_page(about_url, browser_context)
                emails = extract_emails(html)
                for e in emails:
                    if await self.validate_email(e):
                        self.emails.append({"value": e, "confidence": 0.85, "source": "facebook"})

    async def step4_domain_discovery(self):
        # Infer domain from name
        clean_name = re.sub(r'[^a-z0-9]', '', self.name.lower())
        tlds = ['.com', '.in', '.co.uk', '.com.au']
        inferred_domains = [f"{clean_name}{tld}" for tld in tlds]
        
        # Step 5: Email Generation
        prefixes = ['info', 'contact', 'admin', 'support']
        for domain in inferred_domains:
            # Check if domain has MX record before generating
            try:
                await asyncio.to_thread(dns.resolver.resolve, domain, 'MX')
                for p in prefixes:
                    email = f"{p}@{domain}"
                    if await self.validate_email(email):
                        self.emails.append({"value": email, "confidence": 0.40, "source": "generated"})
            except:
                continue

    async def enrich(self) -> Dict:
        init_db()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random_ua())
            
            # Run parallel steps
            await asyncio.gather(
                self.step1_google_search(context),
                self.step2_directory_scraping(context),
                self.step3_facebook_discovery(context),
                self.step4_domain_discovery()
            )
            
            await browser.close()
            
        # Deduplicate and sort
        seen = set()
        unique_emails = []
        
        # Simple keywords from name to filter out unrelated domains (e.g. zhihu, cybo)
        name_keywords = set(re.findall(r'\w+', self.name.lower()))
        
        for e in sorted(self.emails, key=lambda x: x['confidence'], reverse=True):
            email_val = e['value'].lower()
            if email_val not in seen:
                # Basic check: if it's a search result, at least some name keyword should be in the domain
                # or it should be a common provider like gmail/outlook
                domain = email_val.split('@')[1]
                is_common = any(p in domain for p in ['gmail', 'yahoo', 'outlook', 'hotmail', 'icloud'])
                matches_name = any(k in domain for k in name_keywords if len(k) > 3)
                
                if e['source'] == 'generated' or is_common or matches_name:
                    seen.add(email_val)
                    unique_emails.append(e)
        
        final_emails = unique_emails[:5]
        # Overall confidence is the maximum confidence found
        best_conf = max([e['confidence'] for e in final_emails]) if final_emails else 0.0
        
        result = {
            "emails": final_emails,
            "socials": self.socials,
            "sources_checked": self.sources_checked,
            "confidence_score": round(best_conf, 2)
        }
        
        save_enrichment(self.name, self.location, result)
        return result

async def no_website_enrichment(name: str, location: str, phone: Optional[str] = None) -> Dict:
    enricher = NoWebsiteEnricher(name, location, phone)
    return await enricher.enrich()
