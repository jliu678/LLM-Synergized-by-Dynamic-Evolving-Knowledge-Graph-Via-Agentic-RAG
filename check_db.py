#!/usr/bin/env python3
"""
Check database content to see why entities have no descriptions.
"""

import os
import sys
import asyncio

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from agent.db_utils import get_pool, get_entity_by_id
    
    async def check_db_content():
        print("Checking database content...")
        
        try:
            pool = await get_pool()
            
            async with pool.acquire() as conn:
                # Check total entities
                count = await conn.fetchval("SELECT COUNT(*) FROM entities")
                print(f"Total entities in database: {count}")
                
                # Check entities with descriptions
                with_desc = await conn.fetchval(
                    "SELECT COUNT(*) FROM entities WHERE description IS NOT NULL AND description != ''"
                )
                print(f"Entities with descriptions: {with_desc}")
                
                # Sample some entities
                rows = await conn.fetch(
                    "SELECT node_name, node_type, description FROM entities LIMIT 5"
                )
                
                print("\nSample entities:")
                for row in rows:
                    desc = row['description'][:100] + "..." if row['description'] and len(row['description']) > 100 else row['description']
                    print(f"- {row['node_name']} ({row['node_type']}): {desc}")
                
        except Exception as e:
            print(f"Database error: {e}")
    
    asyncio.run(check_db_content())
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")
