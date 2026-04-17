# Entity Matching Engine 🧠

The matcher separates the "noise" (random search hits) from the "signal" (actual business data).

## ⚖️ Scoring Algorithm
Each candidate URL discovered by the search engine is assigned a **Confidence Score (0.0 to 1.0)** based on weighted indices:

| Index | Weight | Description |
|---|---|---|
| **Phone Match** | 0.40 | Exact match of phone digits in the title or snippet. |
| **URL Slug** | 0.25 | Does the business name appear in the URL path? |
| **Name Sim** | 0.20 | Fuzzy matching between business name and page title. |
| **Location** | 0.10 | Presence of the City name in the search result. |
| **Domain** | 0.05 | Match between a known website and the URL domain. |

## 🛡️ Filtering
- **Threshold**: Only candidates with a score **> 0.15** are considered.
- **Noise Filter**: Social tags, reels, and hashtag pages are automatically discarded using `NOISE_URL_MARKERS`.
- **Domain Lock**: Prevents "Wikipedia" or other huge sites from hijacking results unless they are explicitly targeted.
