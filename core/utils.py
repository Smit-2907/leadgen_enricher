import asyncio
import random
from typing import List
from functools import wraps
from thefuzz import fuzz

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def retry_async(retries: int = 3, delay: float = 2.0):
    """Decorator to retry an async function on failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Exponential backoff
                    await asyncio.sleep(delay * (i + 1))
            raise last_exception
        return wrapper
    return decorator

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)

async def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Add a random delay to mimic human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Compare two names and return a score between 0 and 100."""
    if not name1 or not name2:
        return 0.0
    return fuzz.token_sort_ratio(name1.lower(), name2.lower())

def is_valid_match(query_name: str, found_name: str, threshold: int = 60) -> bool:
    """Return True if the found name is a reasonable match for the query."""
    return calculate_name_similarity(query_name, found_name) >= threshold
