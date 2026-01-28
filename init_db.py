"""
Database initialization and setup helper.
"""

import asyncio
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

console = Console()


async def init_postgresql(database_url: str):
    """Initialize PostgreSQL database with schema."""
    console.print("\n[bold cyan]PostgreSQL Initialization[/bold cyan]")
    
    try:
        import asyncpg
        
        # Connect to database
        console.print(f"Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        # Check if pgvector is installed
        console.print("Checking for pgvector extension...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            console.print("[green]✓ pgvector extension enabled[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to enable pgvector: {e}[/red]")
            console.print("[yellow]Install pgvector: https://github.com/pgvector/pgvector[/yellow]")
            await conn.close()
            return False
        
        # Load and execute schema
        schema_path = Path("sql/schema.sql")
        if not schema_path.exists():
            console.print(f"[red]✗ Schema file not found: {schema_path}[/red]")
            await conn.close()
            return False
        
        console.print(f"Loading schema from {schema_path}...")
        schema_sql = schema_path.read_text()
        
        # Execute schema
        await conn.execute(schema_sql)
        console.print("[green]✓ Schema created successfully[/green]")
        
        # Verify tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        console.print(f"\n[bold]Created tables:[/bold]")
        for table in tables:
            console.print(f"  • {table['table_name']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Database initialization failed: {e}[/red]")
        return False


async def test_neo4j(uri: str, user: str, password: str):
    """Test Neo4j connection."""
    console.print("\n[bold cyan]Neo4j Connection Test[/bold cyan]")
    
    try:
        from neo4j import GraphDatabase
        
        console.print(f"Connecting to {uri}...")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Verify connectivity
        driver.verify_connectivity()
        console.print("[green]✓ Neo4j connection successful[/green]")
        
        # Get version
        with driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
            for record in result:
                console.print(f"  {record['name']}: {record['versions'][0]}")
        
        driver.close()
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Neo4j connection failed: {e}[/red]")
        console.print("[yellow]Make sure Neo4j is running on {uri}[/yellow]")
        return False


async def main():
    """Main initialization script."""
    parser = argparse.ArgumentParser(description="Initialize databases for PrimeKG RAG")
    parser.add_argument("--postgres", action="store_true", help="Initialize PostgreSQL")
    parser.add_argument("--neo4j", action="store_true", help="Test Neo4j connection")
    parser.add_argument("--all", action="store_true", help="Initialize all databases")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    
    args = parser.parse_args()
    
    # Load environment
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    console.print("\n[bold cyan]🗄️  Database Initialization[/bold cyan]\n")
    
    # PostgreSQL
    if args.postgres or args.all:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            console.print("[red]✗ DATABASE_URL not set in .env[/red]")
            return
        
        if not args.force:
            if not Confirm.ask("\n[yellow]This will drop and recreate all tables. Continue?[/yellow]"):
                console.print("[yellow]Skipping PostgreSQL initialization[/yellow]")
            else:
                await init_postgresql(database_url)
        else:
            await init_postgresql(database_url)
    
    # Neo4j
    if args.neo4j or args.all:
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if not neo4j_password:
            console.print("[red]✗ NEO4J_PASSWORD not set in .env[/red]")
            return
        
        await test_neo4j(neo4j_uri, neo4j_user, neo4j_password)
    
    if not (args.postgres or args.neo4j or args.all):
        console.print("[yellow]No action specified. Use --postgres, --neo4j, or --all[/yellow]")
        console.print("\nUsage:")
        console.print("  python init_db.py --all          # Initialize all databases")
        console.print("  python init_db.py --postgres     # Initialize PostgreSQL only")
        console.print("  python init_db.py --neo4j        # Test Neo4j only")
    
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
