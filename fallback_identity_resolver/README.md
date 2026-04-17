# Fallback Identity Resolver 🛟

A strictly isolated "rescue" system designed to find contact info for leads that have **zero phone** and **zero website**.

## 🔒 Isolation Contract
This module is designed for zero interference. 
- It has **zero imports** from the rest of the project.
- It is triggered **only** when `phone == null` AND `website == null`.

## 🧠 Logic & Rules

### Confidence Formula
The fallback uses a more rigid formula to prevent hallucination for these high-risk leads:
`confidence = (name_sim * 0.5) + (city_match * 0.3) + (source_weight * 0.2)`

- **REJECT** if name similarity is < 0.6.
- **REJECT** if there is no city match.
- **ACCEPT** only if final confidence is >= 0.7.

### Source Weights
| Source Type | Weight |
|---|---|
| Directory | 1.0 (IndiaMART, Yelp, etc) |
| LinkedIn | 0.9 |
| Facebook | 0.8 |
| Instagram | 0.7 |
| Other | 0.5 |

## 🛠️ Usage
```python
from fallback_identity_resolver.resolver import resolve_missing_identity

result = await resolve_missing_identity(name, city, country)
```
