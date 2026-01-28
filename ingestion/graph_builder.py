"""
Graph builder for creating Graphiti episodes from PrimeKG data.
"""

import logging
from typing import List, Dict, Any
import asyncio
from uuid import uuid4

from agent.graph_utils import get_graphiti_client

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds Graphiti knowledge graph from PrimeKG entities and relationships."""
    
    def __init__(self):
        """Initialize graph builder."""
        self.batch_size = 3  # Small batches for Graphiti
        self.max_content_length = 7000  # Token limit
    
    async def add_entity_to_graph(
        self,
        entity_name: str,
        entity_type: str,
        description: str,
        relationships: List[Dict[str, Any]]
    ):
        """Add an entity and its relationships to the knowledge graph."""
        client = await get_graphiti_client(for_ingestion=True)
        
        # Create episode content
        content = f"{entity_type.upper()}: {entity_name}\n\n"
        
        if description:
            content += f"Description: {description}\n\n"
        
        if relationships:
            content += "Relationships:\n"
            for rel in relationships[:20]:  # Limit to avoid token issues
                content += f"- {rel.get('relation_type', 'related to')} {rel.get('target_name', 'unknown')}\n"
        
        # Truncate if too long
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "..."
        
        # Add to Graphiti
        episode_id = f"primekg_{entity_type}_{uuid4().hex[:8]}"
        
        try:
            await client.add_episode(
                episode_id=episode_id,
                content=content,
                source=f"PrimeKG_{entity_type}"
            )
            logger.debug(f"Added episode for {entity_name}")
        except Exception as e:
            logger.error(f"Failed to add episode for {entity_name}: {e}")
    
    async def build_graph_batch(
        self,
        entities: List[Dict[str, Any]],
        relationships_map: Dict[str, List[Dict[str, Any]]]
    ):
        """Build graph from a batch of entities."""
        tasks = []
        
        for entity in entities:
            entity_id = entity.get('node_id')
            entity_name = entity.get('node_name')
            entity_type = entity.get('node_type')
            description = entity.get('description', '')
            
            # Get relationships for this entity
            rels = relationships_map.get(entity_id, [])
            
            task = self.add_entity_to_graph(
                entity_name,
                entity_type,
                description,
                rels
            )
            tasks.append(task)
            
            # Process in small batches
            if len(tasks) >= self.batch_size:
                await asyncio.gather(*tasks, return_exceptions=True)
                tasks = []
                await asyncio.sleep(0.5)  # Rate limiting
        
        # Process remaining
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
