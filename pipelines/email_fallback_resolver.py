import asyncio
import re
import dns.resolver
import smtplib
import sqlite3
import json
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright
from duckduckgo_search import DDGS

from search.utils import random_ua, extract_emails
from extractors.website_extractor import scrape_website

DB_PATH = 'fallback_results.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_fallback_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
            city TEXT,
            country TEXT,
            emails TEXT,
            source TEXT,
            confidence REAL,
            best_contact_method TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_result(business_name: str, city: str, country: str, emails: List[str], source: str, confidence: float, best_contact_method: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO email_fallback_results (business_name, city, country, emails, source, confidence, best_contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (business_name, city, country, json.dumps(emails), source, confidence, best_contact_method))
    conn.commit()
    conn.close()

def is_valid_email_syntax(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

def has_mx_record(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return bool(answers)
    except:
        return False

def smtp_probe(email: str) -> bool:
    domain = email.split('@')[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mxRecord = str(records[0].exchange)
        
        server = smtplib.SMTP(timeout=3)
        server.set_debuglevel(0)
        
        server.connect(mxRecord)
        server.helo(server.local_hostname)
        server.mail('validate@example.com')
        code, message = server.rcpt(str(email))
        server.quit()
        
        if code == 250:
            return True
        return False
    except Exception:
        # If timeout or block, fail strict validation
        return False

async def validate_emails(emails: List[str]) -> List[str]:
    valid_emails = []
    for email in set(emails):
        if not is_valid_email_syntax(email):
            continue
        domain = email.split('@')[1]
        has_mx = await asyncio.to_thread(has_mx_record, domain)
        if not has_mx:
            continue
        # Skip smtp probe for common providers that block it to prevent false negatives
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            valid_emails.append(email)
            continue
            
        # Probe custom domains
        probe_ok = await asyncio.to_thread(smtp_probe, email)
        if probe_ok:
            valid_emails.append(email)
            
    return valid_emails

def run_search(query: str, max_results: int = 3) -> List[str]:
    urls = []
    try:
        with DDGS(headers={"User-Agent": random_ua()}) as ddgs:
            results = ddgs.text(query, max_results=max_results)
            for r in results:
                urls.append(r['href'])
    except Exception:
        pass
    return urls

async def scrape_html(url: str) -> str:
    try:
        async with httpx.AsyncClient(headers={"User-Agent": random_ua()}, follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url)
            return resp.text
    except Exception:
        return ""

async def scrape_playwright(url: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=random_ua())
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            content = await page.content()
            await browser.close()
            return content
    except Exception:
        return ""

async def step1_directory_discovery(business_name: str, city: str) -> Tuple[List[str], Optional[str]]:
    queries = [
        f'site:justdial.com "{business_name} {city}"',
        f'site:indiamart.com "{business_name} {city}"',
        f'site:sulekha.com "{business_name} {city}"',
        f'site:yelp.com "{business_name} {city}"',
        f'site:yell.com "{business_name} {city}"',
        f'site:yellowpages.com.au "{business_name} {city}"',
    ]
    
    all_urls = []
    for q in queries:
        urls = await asyncio.to_thread(run_search, q, 1)
        all_urls.extend(urls)
        
    for url in all_urls:
        html = await scrape_html(url)
        if not html:
            html = await scrape_playwright(url)
            
        emails = extract_emails(html)
        # Try to find website in html
        soup = BeautifulSoup(html, 'lxml')
        website = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'http' in href and not any(d in href for d in [
                'justdial', 'indiamart', 'sulekha', 'yelp', 'yell', 'yellowpages', 'facebook', 'instagram', 
                'twitter', 'linkedin', 'cybo', 'worldorgs', 'lentlo', 'asklaila', 'tripadvisor', 'crunchbase'
            ]):
                website = href
                break
                
        if website:
            scrape_res = await scrape_website(website)
            emails.extend(scrape_res.get('emails', []))
            
        valid = await validate_emails(emails)
        if valid:
            return valid, "directory"
            
    return [], None

async def step2_domain_discovery(business_name: str, city: str) -> Tuple[List[str], Optional[str]]:
    queries = [
        f'"{business_name} {city} official website"',
        f'"{business_name} {city} contact"'
    ]
    all_urls = []
    for q in queries:
        urls = await asyncio.to_thread(run_search, q, 3)
        all_urls.extend(urls)
        
    domains = set()
    for url in all_urls:
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            domain = match.group(1).lower()
            if not any(noise in domain for noise in [
                'justdial', 'yelp', 'facebook', 'instagram', 'linkedin', 'twitter', 'youtube',
                'cybo', 'worldorgs', 'lentlo', 'indiamart', 'sulekha', 'manta', 'tradeindia'
            ]):
                domains.add(domain)
                
    for domain in domains:
        prefixes = ["info", "contact", "hello", "support", "admin"]
        generated = [f"{p}@{domain}" for p in prefixes]
        valid = await validate_emails(generated)
        if valid:
            return valid, "domain"
            
    return [], None

async def step3_facebook_extraction(business_name: str, city: str) -> Tuple[List[str], Optional[str]]:
    q = f'"{business_name} {city} facebook"'
    urls = await asyncio.to_thread(run_search, q, 1)
    
    for url in urls:
        if 'facebook.com' in url:
            html = await scrape_playwright(url)
            emails = extract_emails(html)
            valid = await validate_emails(emails)
            if valid:
                return valid, "facebook"
                
    return [], None

async def step4_generic_email_search(business_name: str) -> Tuple[List[str], Optional[str]]:
    queries = [
        f'"{business_name}" "@gmail.com"',
        f'"{business_name}" "email"',
        f'"{business_name}" "contact"'
    ]
    all_urls = []
    for q in queries:
        urls = await asyncio.to_thread(run_search, q, 2)
        all_urls.extend(urls)
        
    all_emails = []
    for url in set(all_urls):
        html = await scrape_html(url)
        all_emails.extend(extract_emails(html))
        
    valid = await validate_emails(all_emails)
    if valid:
        return valid, "search"
        
    return [], None

def format_success(emails: List[str], source: str) -> Dict[str, Any]:
    confidence_map = {
        "directory": 0.9,
        "facebook": 0.6,
        "domain": 0.4,
        "search": 0.3
    }
    return {
        "emails": emails,
        "source": source,
        "confidence": confidence_map.get(source, 0.0),
        "best_contact_method": "email"
    }

def format_failure() -> Dict[str, Any]:
    return {
        "emails": [],
        "best_contact_method": "phone",
        "message": "No publicly available email found"
    }

async def resolve_email_fallback(business_name: str, city: str, country: str = "unknown") -> Dict[str, Any]:
    init_db()
    
    # Priority 1: Directory Discovery
    emails, source = await step1_directory_discovery(business_name, city)
    
    # Priority 2: Domain Discovery
    if not emails:
        emails, source = await step2_domain_discovery(business_name, city)
        
    # Priority 3: Facebook Email Extraction
    if not emails:
        emails, source = await step3_facebook_extraction(business_name, city)
        
    # Priority 4: Generic Email Search
    if not emails:
        emails, source = await step4_generic_email_search(business_name)
        
    if emails:
        result = format_success(emails, source)
    else:
        result = format_failure()
        
    save_result(
        business_name,
        city,
        country,
        result.get("emails", []),
        result.get("source", "none"),
        result.get("confidence", 0.0),
        result.get("best_contact_method", "manual")
    )
    
    return result

