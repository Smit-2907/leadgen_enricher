import asyncio
from core.models import LeadIn
from core.engine import EnrichmentEngine
from rich.console import Console

console = Console()

async def stress_test():
    # Test cases designed to trigger fallbacks
    test_leads = [
        # 1. Lead with no website (triggers Search + Phone + Directories)
        LeadIn(business_name="Mahesh Lunch Home", location="Pune, Maharashtra", phone="+91 20 6603 2230"),
        
        # 2. Lead with website but no email (triggers WHOIS)
        LeadIn(business_name="Sunrise Dental Clinic", location="Pune", website="sunrisedental.in"),
        
        # 3. Lead that only has a social presence (triggers Social Bio Scrape)
        LeadIn(business_name="The Burger Barn Cafe", location="Pune")
    ]
    
    engine = EnrichmentEngine()
    
    for lead in test_leads:
        console.print(f"\n[bold green]STRESS TEST:[/bold green] {lead.business_name}")
        result = await engine.enrich_lead(lead)
        
        console.print(f"Emails: {result.emails}")
        console.print(f"Socials Count: {len(result.social_profiles)}")
        for p in result.social_profiles[:3]:
            console.print(f" - {p.platform}: {p.url}")
            
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(stress_test())
