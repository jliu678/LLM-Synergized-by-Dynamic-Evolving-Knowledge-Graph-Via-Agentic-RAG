#!/usr/bin/env python3
"""
Test Graphiti graph building directly.
"""

import os
import sys
import asyncio
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_graph_builder():
    """Test Graphiti graph building directly."""
    print("Testing Graphiti graph builder...")
    
    try:
        from ingestion.graph_builder import GraphBuilder
        from agent.db_utils import get_pool
        
        # Initialize graph builder
        graph_builder = GraphBuilder()
        
        # Get sample data from PostgreSQL
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            # Get sample entities
            entities_query = """
            SELECT node_id, node_name, node_type 
            FROM entities 
            LIMIT 5
            """
            entities = await conn.fetch(entities_query)
            
            # Get sample relationships
            relationships_query = """
            SELECT 
                e1.node_name as source_name,
                e1.node_type as source_type,
                e2.node_name as target_name,
                e2.node_type as target_type,
                r.relation_type
            FROM relationships r
            JOIN entities e1 ON r.source_entity_id = e1.id
            JOIN entities e2 ON r.target_entity_id = e2.id
            LIMIT 5
            """
            relationships = await conn.fetch(relationships_query)
        
        print(f"Found {len(entities)} entities and {len(relationships)} relationships in PostgreSQL")
        
        # Prepare data for graph builder
        entities_list = []
        for entity in entities:
            entities_list.append({
                'node_id': str(entity['node_id']),
                'node_name': str(entity['node_name']),
                'node_type': str(entity['node_type']),
                'description': str(entity['node_name'])  # Use name as description
            })
        
        # Build relationships map
        relationships_map = {}
        for rel in relationships:
            source_id = str(rel['source_name'])  # Use name as ID for this test
            if source_id not in relationships_map:
                relationships_map[source_id] = []
            relationships_map[source_id].append({
                'relation_type': str(rel['relation_type']),
                'target_name': str(rel['target_name'])
            })
        
        print(f"Prepared {len(entities_list)} entities for graph building")
        print(f"Prepared {len(relationships_map)} relationship groups")
        
        # Test graph building
        print("Building graph...")
        await graph_builder.build_graph_batch(entities_list, relationships_map)
        print("✅ Graph building completed!")
        
    except Exception as e:
        print(f"❌ Graph building failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_graph_builder())
