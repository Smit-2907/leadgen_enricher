# Extraction Layer ⛏️

This layer performs the "Deep Scraping" once a URL has been verified as belonging to the lead.

## 🛠️ Extraction Strategies

### 1. Website Extractor (`website_extractor.py`)
Uses a **Dual-Mode** approach:
- **Fast Mode**: Attempts a lightweight `httpx` GET request.
- **Stealth Mode**: Falls back to **Playwright** if the site is a Single Page App (SPA) or has basic bot protection.
- **Recursive Scan**: If no email is on the homepage, it automatically crawls "Contact" and "About" subpages.

### 2. Social Bio Sniffer (`social_extractor.py`)
Targets Instagram, Facebook, and LinkedIn.
- Uses **Playwright Stealth** to bypass security.
- Specifically targets the "About" and "Bio" sections where emails are most likely found.

### 3. Snippet Harvester (`snippet_extractor.py`)
Extracts emails directly from search engine fragments. This is the fastest method and requires **zero network calls** because the data was already fetched by the search engine.
