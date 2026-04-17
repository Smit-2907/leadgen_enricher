#!/usr/bin/env python3
"""
LeadGenX — Global Identity Resolution Engine
Entry point CLI
"""
import asyncio
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from pipelines.resolver import resolve_identity

console = Console()

async def run():
    console.print(Panel.fit(
        "[bold cyan]LeadGenX[/bold cyan] [white]Global Identity Resolution Engine[/white]\n"
        "[dim]Searches 20+ sources · Works India, USA, UK, Australia[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))

    name    = console.input("[bold yellow]Business Name :[/bold yellow] ").strip()
    city    = console.input("[bold yellow]City / Location:[/bold yellow] ").strip()
    phone   = console.input("[bold yellow]Phone (optional):[/bold yellow] ").strip() or None
    website = console.input("[bold yellow]Website (optional):[/bold yellow] ").strip() or None

    console.print("\n[dim]Running enrichment pipeline...[/dim]\n")

    result = await resolve_identity(
        business_name=name,
        city=city,
        phone=phone,
        website=website,
    )

    # ── Emails ──────────────────────────────────────────────────────────────
    email_table = Table(title="📧 Emails", box=box.ROUNDED, border_style="green")
    email_table.add_column("Email", style="bold green")
    email_table.add_column("Confidence")
    conf = result.confidence.get("email", result.confidence.get("guessed_emails", 0))
    if result.emails:
        for e in result.emails:
            email_table.add_row(e, f"{conf:.0%}")
    else:
        email_table.add_row("[dim]NOT FOUND[/dim]", "—")

    # ── Socials ─────────────────────────────────────────────────────────────
    social_table = Table(title="🔗 Social Profiles", box=box.ROUNDED, border_style="blue")
    social_table.add_column("Platform", style="bold blue")
    social_table.add_column("URL")
    any_social = False
    for platform, url in result.socials.items():
        if url:
            social_table.add_row(platform.capitalize(), url)
            any_social = True
    if not any_social:
        social_table.add_row("[dim]NOT FOUND[/dim]", "—")

    # ── Directories ─────────────────────────────────────────────────────────
    dir_table = Table(title="📂 Directories", box=box.ROUNDED, border_style="yellow")
    dir_table.add_column("URL")
    if result.directories:
        for d in result.directories:
            dir_table.add_row(d)
    else:
        dir_table.add_row("[dim]None discovered[/dim]")

    console.print(email_table)
    console.print(social_table)
    console.print(dir_table)

    # ── Summary ─────────────────────────────────────────────────────────────
    method_color = {"email": "green", "social": "cyan", "phone": "yellow"}.get(result.best_contact_method, "white")
    console.print(Panel(
        f"[bold]Best Contact Method:[/bold] [{method_color}]{result.best_contact_method.upper()}[/{method_color}]\n"
        f"[dim]{result.reasoning}[/dim]\n\n"
        f"[dim]Sources: {' → '.join(result.sources_used)}[/dim]",
        title="Summary",
        border_style=method_color,
    ))


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[red]Aborted.[/red]")
        sys.exit(0)
