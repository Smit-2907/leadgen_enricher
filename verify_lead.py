import asyncio
from core.models import LeadIn
from core.engine import EnrichmentEngine
from rich.console import Console

console = Console()

async def test_cases():
    test_leads = [
        # Case 1: Well known business in India
        LeadIn(business_name="Sunrise Dental Clinic", location="Pune, India", website="sunrisedental.in"),
        # Case 2: Business without website
        LeadIn(business_name="Mahesh Lunch Home", location="Pune, Maharashtra")
    ]
    
    engine = EnrichmentEngine()
    
    for lead in test_leads:
        console.print(f"\n[bold green]Testing Lead:[/bold green] {lead.business_name} in {lead.location}")
        result = await engine.enrich_lead(lead)
        
        console.print(f"Emails found: {result.emails}")
        console.print("Socials found:")
        for p in result.social_profiles:
            console.print(f" - {p.platform}: {p.url}")
            
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(test_cases())
