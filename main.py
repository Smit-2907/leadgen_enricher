import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from core.models import LeadIn
from core.engine import EnrichmentEngine

console = Console()

async def run_enrichment():
    console.print(Panel.fit(
        "[bold cyan]LeadGenX: Bullet-Proof Edition[/bold cyan]\n"
        "[dim]Maximum Reliability Lead Enrichment[/dim]",
        border_style="cyan"
    ))

    name = console.input("[bold yellow]Enter Business Name:[/bold yellow] ")
    loc = console.input("[bold yellow]Enter Location:[/bold yellow] ")
    web = console.input("[bold yellow]Enter Website (optional):[/bold yellow] ")
    phone = console.input("[bold yellow]Enter Phone (optional):[/bold yellow] ")
    
    lead = LeadIn(
        business_name=name, 
        location=loc, 
        website=web if web else None,
        phone=phone if phone else None
    )
    
    engine = EnrichmentEngine()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Phase 1: Search Engines & Website...", total=None)
        progress.add_task(description="Phase 2: Phone Reverse Lookup...", total=None)
        progress.add_task(description="Phase 3: Directory Fallbacks...", total=None)
        progress.add_task(description="Phase 4: Last Resort (WHOIS/YouTube)...", total=None)
        progress.add_task(description="Phase 5: Social Bio Extraction...", total=None)
        
        try:
            result = await engine.enrich_lead(lead)
        finally:
            await engine.shutdown()

    # Display Results
    table = Table(title=f"Bulk-Enriched Results for {name}", show_header=True, header_style="bold green")
    table.add_column("Property", style="dim")
    table.add_column("Value")

    table.add_row("Emails Found", "\n".join(result.emails) if result.emails else "[red]NONE[/red]")
    
    socials = "\n".join([f"{p.platform}: {p.url}" for p in result.social_profiles])
    table.add_row("Social Profiles", socials if socials else "[red]NONE[/red]")
    
    table.add_row("Sources Hit", ", ".join(result.sources))

    console.print(table)

if __name__ == "__main__":
    try:
        asyncio.run(run_enrichment())
    except KeyboardInterrupt:
        console.print("\n[red]Exiting...[/red]")
        sys.exit(0)
