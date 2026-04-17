# Search Layer 📡

The search layer is responsible for discovering all possible digital footprints of a business across the global web.

## 🧠 Components

### `query_builder.py`
This is the intelligence center. It doesn't just search for the business name; it builds specialized queries:
- **Social Dorks**: `site:instagram.com "Business Name"`
- **Deep Email Hunts**: `"Business Name" "City" "@gmail.com"`
- **Directory Dorks**: `site:justdial.com "Business Name"`
- **Phone Reverse Lookups**: Searching for the raw digits to find listings.

### `country_detector.py`
Detects the business region using:
1. Phone International Prefixes (`+91` -> India, `+1` -> USA, etc.)
2. Keyword matching on the city/location string.

## ⚡ Performance
All searches are parallelized using `asyncio.to_thread`. Each search is wrapped in an **8.0s timeout** to prevent the pipeline from hanging on slow search engine responses.
