"""
Utility script to verify system setup and configuration.
"""

import os
import sys
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"{version.major}.{version.minor}.{version.micro}"


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    return env_path.exists(), str(env_path.absolute())


def check_dependencies():
    """Check if key dependencies are installed."""
    deps = {
        "pydantic-ai": "pydantic_ai",
        "graphiti-core": "graphiti_core",
        "fastapi": "fastapi",
        "asyncpg": "asyncpg",
        "neo4j": "neo4j",
        "pandas": "pandas"
    }
    
    results = {}
    for name, import_name in deps.items():
        try:
            __import__(import_name)
            results[name] = "✓ Installed"
        except ImportError:
            results[name] = "✗ Missing"
    
    return results


async def check_database_connection():
    """Check PostgreSQL connection."""
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False, "DATABASE_URL not set in .env"
    
    try:
        import asyncpg
        conn = await asyncpg.connect(database_url, timeout=5)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        return True, version.split(",")[0]
    except Exception as e:
        return False, str(e)


async def check_neo4j_connection():
    """Check Neo4j connection."""
    from dotenv import load_dotenv
    load_dotenv()
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not password:
        return False, "NEO4J_PASSWORD not set in .env"
    
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True, f"Connected to {uri}"
    except Exception as e:
        return False, str(e)


def check_data_directory():
    """Check if data directory exists and has files."""
    data_dir = Path("data")
    if not data_dir.exists():
        return False, "data/ directory not found"
    
    kg_file = data_dir / "kg.csv"
    if kg_file.exists():
        size_mb = kg_file.stat().st_size / (1024 * 1024)
        return True, f"kg.csv found ({size_mb:.1f} MB)"
    
    return False, "kg.csv not found (run ingestion with --download)"


async def main():
    """Run all checks."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔍 System Verification[/bold cyan]\n"
        "[dim]Checking PrimeKG RAG Setup[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    # Create results table
    table = Table(title="Configuration Check", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=30)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim")
    
    # Python version
    ok, version = check_python_version()
    table.add_row(
        "Python Version",
        "[green]✓ OK[/green]" if ok else "[red]✗ FAIL[/red]",
        version
    )
    
    # Environment file
    ok, path = check_env_file()
    table.add_row(
        ".env File",
        "[green]✓ Found[/green]" if ok else "[yellow]⚠ Missing[/yellow]",
        path if ok else "Copy .env.example to .env"
    )
    
    # Dependencies
    deps = check_dependencies()
    all_installed = all("✓" in status for status in deps.values())
    table.add_row(
        "Dependencies",
        "[green]✓ OK[/green]" if all_installed else "[yellow]⚠ Partial[/yellow]",
        f"{sum('✓' in s for s in deps.values())}/{len(deps)} installed"
    )
    
    # Database
    ok, msg = await check_database_connection()
    table.add_row(
        "PostgreSQL",
        "[green]✓ Connected[/green]" if ok else "[red]✗ Failed[/red]",
        msg[:50] + "..." if len(msg) > 50 else msg
    )
    
    # Neo4j
    ok, msg = await check_neo4j_connection()
    table.add_row(
        "Neo4j",
        "[green]✓ Connected[/green]" if ok else "[red]✗ Failed[/red]",
        msg[:50] + "..." if len(msg) > 50 else msg
    )
    
    # Data
    ok, msg = check_data_directory()
    table.add_row(
        "PrimeKG Data",
        "[green]✓ Ready[/green]" if ok else "[yellow]⚠ Missing[/yellow]",
        msg
    )
    
    console.print(table)
    console.print()
    
    # Detailed dependency check
    if not all_installed:
        console.print("[bold yellow]Dependency Details:[/bold yellow]")
        for name, status in deps.items():
            console.print(f"  {status} {name}")
        console.print()
    
    # Next steps
    console.print("[bold cyan]Next Steps:[/bold cyan]")
    if not check_env_file()[0]:
        console.print("  1. Copy .env.example to .env and configure")
    if not await check_database_connection():
        console.print("  2. Set up PostgreSQL and run sql/schema.sql")
    if not await check_neo4j_connection():
        console.print("  3. Start Neo4j and configure credentials")
    if not check_data_directory()[0]:
        console.print("  4. Run: python -m ingestion.ingest --download --limit 1000")
    
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
