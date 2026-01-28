#!/usr/bin/env python3
"""
Check Neo4j database state and node counts.
"""

import os
import sys
import asyncio
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def check_neo4j_state():
    """Check Neo4j database state, schema, and data."""
    print("Checking Neo4j database state...")
    
    try:
        from agent.graph_utils import GraphitiClient
        
        # Create Graphiti client to access Neo4j
        client = GraphitiClient()
        await client.initialize()
        
        # Access the underlying Neo4j driver from Graphiti
        if hasattr(client.graphiti, 'driver') and client.graphiti.driver:
            driver = client.graphiti.driver
        else:
            # Try to access Neo4j directly
            from neo4j import GraphDatabase
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD")
            
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        session = driver.session()
        
        print("\n=== Database Info ===")
        
        # Check database info
        try:
            result = await session.run("CALL db.info()")
            info = await result.single()
            print(f"Database: {info.get('name', 'neo4j')}")
        except Exception as e:
            print(f"Database info query failed: {e}")
            print("Database: neo4j (assumed)")
        
        print("\n=== Node Counts ===")
        
        # Count all nodes
        result = await session.run("MATCH (n) RETURN count(n) as total_nodes")
        total = (await result.single())['total_nodes']
        print(f"Total nodes: {total}")
        
        # Count nodes by label
        result = await session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
        records = []
        async for record in result:
            records.append(record)
        
        for record in records:
            labels = record['labels']
            count = record['count']
            print(f"  {labels}: {count}")
        
        print("\n=== Relationship Counts ===")
        
        # Count all relationships
        result = await session.run("MATCH ()-[r]->() RETURN count(r) as total_rels")
        total_rels = (await result.single())['total_rels']
        print(f"Total relationships: {total_rels}")
        
        # Count relationships by type
        result = await session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC")
        records = []
        async for record in result:
            records.append(record)
        
        for record in records:
            rel_type = record['type']
            count = record['count']
            print(f"  {rel_type}: {count}")
        
        print("\n=== Sample Data ===")
        
        # Show sample nodes if any exist
        if total > 0:
            result = await session.run("MATCH (n) RETURN n LIMIT 5")
            records = []
            async for record in result:
                records.append(record)
            
            for i, record in enumerate(records):
                node = record['n']
                print(f"Node {i+1}: {dict(node)}")
        else:
            print("No nodes found in database")
        
        await session.close()
        
        # Also check PostgreSQL for entities
        print("\n=== PostgreSQL Entity Count ===")
        try:
            from agent.db_utils import get_pool
            pool = await get_pool()
            
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM entities")
                print(f"PostgreSQL entities: {result}")
                
                result = await conn.fetchval("SELECT COUNT(*) FROM entity_embeddings")
                print(f"PostgreSQL embeddings: {result}")
                
                result = await conn.fetchval("SELECT COUNT(*) FROM relationships")
                print(f"PostgreSQL relationships: {result}")
                
        except Exception as e:
            print(f"PostgreSQL check failed: {e}")
            
    except Exception as e:
        print(f"Error checking Neo4j: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_neo4j_state())
