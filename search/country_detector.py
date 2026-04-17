"""
Country Detection — classifies business location into supported regions.
"""
import re
from search.models import Country

# Mapping of keywords to countries
_INDIA_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "ahmedabad",
    "pune", "kolkata", "chennai", "surat", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "pimpri",
    "patna", "vadodara", "coimbatore", "ludhiana", "agra", "nashik",
    "india", "gujarat", "maharashtra", "karnataka", "rajasthan",
    "uttar pradesh", "west bengal", "tamil nadu", "telangana", "kerala",
    "bihar", "madhya pradesh", "andhra pradesh",
}
_USA_KEYWORDS = {
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "san jose", "austin", "jacksonville",
    "san francisco", "seattle", "denver", "nashville", "usa", "united states",
    "california", "texas", "florida", "new york state",
}
_UK_KEYWORDS = {
    "london", "manchester", "birmingham", "glasgow", "liverpool", "bristol",
    "leeds", "edinburgh", "sheffield", "uk", "united kingdom", "england",
    "scotland", "wales",
}
_AUSTRALIA_KEYWORDS = {
    "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra",
    "hobart", "darwin", "australia", "victoria", "queensland",
    "new south wales", "western australia",
}

# Phone prefix mapping
_PHONE_CODES = {
    "+91": "india", "0091": "india",
    "+1": "usa",    "001": "usa",
    "+44": "uk",    "0044": "uk",
    "+61": "australia", "0061": "australia",
}


def detect_country(city: str, phone: str = None) -> Country:
    text = city.lower()

    # 1. Phone code takes priority
    if phone:
        clean = re.sub(r'\s', '', phone)
        for code, country in _PHONE_CODES.items():
            if clean.startswith(code):
                return country  # type: ignore

    # 2. Keyword match on city/address string
    words = set(re.findall(r'[\w]+', text))
    bigrams = set()
    tokens = text.split()
    for i in range(len(tokens) - 1):
        bigrams.add(tokens[i] + " " + tokens[i + 1])
    combined = words | bigrams

    if combined & _INDIA_CITIES:
        return "india"
    if combined & _USA_KEYWORDS:
        return "usa"
    if combined & _UK_KEYWORDS:
        return "uk"
    if combined & _AUSTRALIA_KEYWORDS:
        return "australia"

    return "unknown"
