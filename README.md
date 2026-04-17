# LeadGenX: Global Identity Resolution Engine

LeadGenX is a high-performance, modular system designed to find missing contact information (emails & social profiles) for businesses globally. It targets small-to-medium businesses that often lack a clear digital footprint.

## 🚀 Key Features
- **Global Coverage**: Intelligent routing for leads in India, USA, UK, and Australia.
- **Multi-Layered Discovery**:
    - **Deep Web Dorking**: Extracts contact info directly from search engine snippets.
    - **Stealth Scaping**: Bypasses bot detection on Instagram, Facebook, and LinkedIn.
    - **Directory Sniffing**: Cross-references local directories (JustDial, Yelp, YellowPages).
- **Identity Matching**: Uses fuzzy name matching and weighted confidence scoring to eliminate false positives.
- **Ultra-Fast**: Parallelized execution brings search times down to <10 seconds per lead.

## 📂 Project Structure
- `search/`: Query generation and engine orchestration.
- `extractors/`: Specialized modules for Websites, Social Bios, and Snippets.
- `match/`: The Identity Matching Engine (weighted scoring & confidence).
- `pipelines/`: Main entry point for resolving a business identity.
- `cache/`: Session-level performance caching.

## 🛠️ Usage
Run the engine via the CLI:
```bash
uv run python main.py
```

### Integration
You can use the resolver in your own Python projects:
```python
from pipelines.resolver import resolve_identity

result = await resolve_identity(
    business_name="7th Heaven Events",
    city="Kolkata",
    phone="+91..."
)
print(result.emails)
```

## 📜 Requirements
Managed via `uv`. 
Key dependencies: `playwright`, `duckduckgo-search`, `rapidfuzz`, `httpx`, `beautifulsoup4`.
