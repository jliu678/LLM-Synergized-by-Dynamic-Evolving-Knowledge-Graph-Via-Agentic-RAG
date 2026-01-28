"""
Main ingestion script for PrimeKG data.
"""

import asyncio
import logging
import argparse
import sys
import os
from typing import Optional
from uuid import uuid4

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ingestion.data_loader import PrimeKGLoader, download_primekg_data
from ingestion.embedder import Embedder
from ingestion.graph_builder import GraphBuilder
from agent.db_utils import (
    get_pool,
    close_pool,
    insert_entity,
    insert_entity_embedding,
    insert_relationship,
    get_entity_by_node_id
)
from agent.graph_utils import close_graphiti
from agent.models import Entity, EntityEmbedding, Relationship
from agent.providers import get_embedding_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_primekg(
    data_dir: str = "./data",
    limit: Optional[int] = None,
    skip_graph: bool = False,
    download: bool = False,
    random_sample: bool = False
):
    """
    Main ingestion pipeline for PrimeKG data.
    
    Args:
        data_dir: Directory for PrimeKG data files
        limit: Limit number of entities to process (for testing)
        skip_graph: Skip Graphiti graph building
        download: Download PrimeKG data first
        random_sample: Use random sampling instead of first N rows
    """
    logger.info("Starting PrimeKG ingestion pipeline...")
    
    # Download data if requested
    if download:
        logger.info("Downloading PrimeKG data...")
        await download_primekg_data(data_dir)
    
    # Load data
    loader = PrimeKGLoader(data_dir)
    kg_df = loader.load_kg(limit=limit, random_sample=random_sample)
    entities_df = loader.extract_entities(kg_df)
    relationships_df = loader.extract_relationships(kg_df)
    
    logger.info(f"Loaded {len(entities_df)} entities and {len(relationships_df)} relationships")
    
    # Initialize components
    embedder = Embedder()
    graph_builder = GraphBuilder() if not skip_graph else None
    
    # Process entities
    logger.info("Processing entities...")
    entity_map = {}  # Map node_id to database UUID
    
    for idx, row in entities_df.iterrows():
        try:
            # Create entity
            entity = Entity(
                node_index=int(row['node_index']),
                node_id=str(row['node_id']),
                node_name=str(row['node_name']),
                node_type=str(row['node_type']),
                description=None,  # Will be added from features if available
                source="PrimeKG"
            )
            
            # Insert entity
            entity_id = await insert_entity(entity)
            entity_map[entity.node_id] = entity_id
            
            # Generate and insert embedding if entity has a name
            if entity.node_name:
                try:
                    # Create context-aware embedding text
                    # e.g. "CD7 (gene/protein)" instead of just "CD7"
                    if entity.node_type and entity.node_type != "nan":
                        embedding_text = f"Biomedical {entity.node_type}: {entity.node_name}. Source: PrimeKG."
                    else:
                        embedding_text = f"Biomedical entity: {entity.node_name}. Source: PrimeKG."
                    
                    embedding_vector = await embedder.generate_embedding(embedding_text)
                    
                    embedding = EntityEmbedding(
                        entity_id=entity_id,
                        embedding=embedding_vector,
                        embedding_model=get_embedding_model()
                    )
                    
                    await insert_entity_embedding(embedding)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for {entity.node_name}: {e}")
            
            if (idx + 1) % 100 == 0:
                logger.info(f"Processed {idx + 1}/{len(entities_df)} entities")
                
        except Exception as e:
            logger.error(f"Failed to process entity {row.get('node_name', 'unknown')}: {e}")
            continue
    
    logger.info(f"Completed entity processing: {len(entity_map)} entities inserted")
    
    # Process relationships
    logger.info("Processing relationships...")
    relationship_count = 0
    
    for idx, row in relationships_df.iterrows():
        try:
            source_id = entity_map.get(str(row['source_id']))
            target_id = entity_map.get(str(row['target_id']))
            
            if source_id and target_id:
                relationship = Relationship(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relation_type=str(row['relation_type']),
                    display_relation=str(row.get('display_relation', '')),
                    source_type=str(row.get('source_type', '')),
                    target_type=str(row.get('target_type', ''))
                )
                
                await insert_relationship(relationship)
                relationship_count += 1
            
            if (idx + 1) % 1000 == 0:
                logger.info(f"Processed {idx + 1}/{len(relationships_df)} relationships")
                
        except Exception as e:
            logger.error(f"Failed to process relationship: {e}")
            continue
    
    logger.info(f"Completed relationship processing: {relationship_count} relationships inserted")
    
    # Build Graphiti graph
    if graph_builder and not skip_graph:
        logger.info("Building Graphiti knowledge graph...")
        
        # Prepare data for graph builder
        entities_list = []
        for _, row in entities_df.head(min(1000, len(entities_df))).iterrows():  # Limit for Graphiti
            entities_list.append({
                'node_id': str(row['node_id']),
                'node_name': str(row['node_name']),
                'node_type': str(row['node_type']),
                'description': str(row['node_name'])  # Use name as description for now
            })
        
        # Build relationships map
        relationships_map = {}
        for _, row in relationships_df.iterrows():
            source_id = str(row['source_id'])
            if source_id not in relationships_map:
                relationships_map[source_id] = []
            relationships_map[source_id].append({
                'relation_type': str(row['relation_type']),
                'target_name': str(row.get('target_id', 'unknown'))
            })
        
        await graph_builder.build_graph_batch(entities_list, relationships_map)
        logger.info("Graphiti graph building complete")
    
    logger.info("PrimeKG ingestion pipeline complete!")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest PrimeKG data into the system")
    parser.add_argument("--download", action="store_true", help="Download PrimeKG data first")
    parser.add_argument("--clean", action="store_true", help="Clean existing data (not implemented)")
    parser.add_argument("--skip-graph", action="store_true", help="Skip Graphiti graph building")
    parser.add_argument("--limit", type=int, help="Limit number of entities to process")
    parser.add_argument("--random-sample", action="store_true", help="Use random sampling instead of first N rows")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--data-dir", default="./data", help="Data directory")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        await ingest_primekg(
            data_dir=args.data_dir,
            limit=args.limit,
            skip_graph=args.skip_graph,
            download=args.download,
            random_sample=args.random_sample
        )
    finally:
        await close_pool()
        await close_graphiti()


if __name__ == "__main__":
    asyncio.run(main())
