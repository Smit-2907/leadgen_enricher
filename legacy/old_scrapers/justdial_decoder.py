import asyncio
import re
from typing import List, Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from core.utils import get_random_user_agent

class JustDialDecoder:
    async def get_decoded_phone(self, jd_url: str) -> Optional[str]:
        """Visit JD URL and attempt to decode the phone number."""
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=get_random_user_agent())
                await Stealth().apply_stealth_async(page)
                
                await page.goto(jd_url, wait_until="networkidle", timeout=30000)
                
                # JD phone numbers are often in a container with class 'tel' or similar
                # We prioritize text that a real user would see/hear (ARIA or innerText)
                phone_elements = await page.query_selector_all(".mobilesv, .tel, .contact-info")
                found_digits = []
                
                for el in phone_elements:
                    text = await el.inner_text()
                    # If the number is rendered as text by the browser (some JS does this)
                    digits = re.sub(r"\D", "", text)
                    if len(digits) >= 10:
                        return digits
                
                # Fallback: Look for the 'call' button href
                call_btn = await page.query_selector("a[href^='tel:']")
                if call_btn:
                    href = await call_btn.get_attribute("href")
                    return href.replace("tel:", "").strip()

            except Exception as e:
                # print(f"JustDialDecoder error: {e}")
                pass
            finally:
                await browser.close()
        return None
