import asyncio
import whois
from typing import Optional
from core.utils import EMAIL_REGEX
import re

class WhoisLookup:
    async def get_registrant_email(self, domain: str) -> Optional[str]:
        """Lookup WHOIS data for a domain and extract emails."""
        if not domain:
            return None
        
        # Clean domain
        domain = domain.split('//')[-1].split('/')[0].replace('www.', '')
        
        try:
            # whois.whois is sync, wrap in thread
            w = await asyncio.to_thread(whois.whois, domain)
            
            # The library often returns email in different fields
            email_fields = ['email', 'emails', 'registrant_email']
            found_emails = []
            
            for field in email_fields:
                val = getattr(w, field, None)
                if val:
                    if isinstance(val, list):
                        found_emails.extend(val)
                    else:
                        found_emails.append(str(val))
            
            # Validate and return first good email
            for email in found_emails:
                if re.match(EMAIL_REGEX, email):
                    # Filter out common placeholders
                    if not any(x in email.lower() for x in ['domainsbyproxy', 'privacy', 'whois']):
                        return email.lower()
                        
        except Exception as e:
            # Silent fail for WHOIS as many servers block automated lookups
            pass
            
        return None
