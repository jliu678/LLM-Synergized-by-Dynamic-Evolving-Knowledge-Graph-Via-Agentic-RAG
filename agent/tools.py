"""
Agent tools for PrimeKG knowledge retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from agent.db_utils import (
    vector_search,
    hybrid_search,
    get_entity_by_id,
    list_entities,
    get_entity_relationships_db
)
from agent.graph_utils import search_knowledge_graph, get_entity_relationships
from ingestion.embedder import generate_embedding

logger = logging.getLogger(__name__)


async def vector_search_tool(
    query: str,
    limit: int = 10,
    entity_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search over entity descriptions.
    
    Args:
        query: Search query
        limit: Maximum number of results
        entity_type: Filter by entity type (disease, drug, protein, etc.)
    
    Returns:
        List of matching entities with similarity scores
    """
    try:
        # Generate query embedding
        try:
            query_embedding = await generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for vector search: {e}")
            return []
        
        # Search
        results = await vector_search(
            query_embedding=query_embedding,
            limit=limit,
            threshold=0.3,
            entity_type=entity_type
        )
        
        # Format results and deduplicate
        seen_entities = set()
        formatted = []
        for result in results:
            entity_key = (result.node_name, result.node_type)  # Deduplicate by name and type
            if entity_key not in seen_entities:
                formatted.append({
                    "entity_id": str(result.entity_id),
                    "name": result.node_name,
                    "type": result.node_type,
                    "description": result.description or f"{result.node_name} is a {result.node_type} in the biomedical knowledge graph.",
                    "similarity": round(result.similarity, 3) if result.similarity else 0
                })
                seen_entities.add(entity_key)
        
        logger.info(f"Vector search for '{query}' returned {len(formatted)} results")
        # Limit results to prevent context overload
        return formatted[:8]
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


async def graph_search_tool(query: str) -> List[Dict[str, Any]]:
    """
    Search the Graphiti knowledge graph for facts and relationships.
    
    Args:
        query: Search query
    
    Returns:
        List of facts from the knowledge graph
    """
    try:
        results = await search_knowledge_graph(query)
        
        # Format results and deduplicate
        seen_facts = set()
        formatted = []
        for result in results:
            fact_text = result.get("fact", "").strip()
            # Deduplicate by fact text (normalize whitespace)
            normalized_fact = ' '.join(fact_text.split())
            if normalized_fact and normalized_fact not in seen_facts:
                formatted.append({
                    "fact": fact_text,
                    "episodes": result.get("episode_ids", []),
                    "valid_at": str(result.get("valid_at", "")) if result.get("valid_at") else None
                })
                seen_facts.add(normalized_fact)
        
        logger.info(f"Graph search for '{query}' returned {len(formatted)} results")
        # Limit results to prevent context overload
        return formatted[:8]
        
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        return []


async def hybrid_search_tool(
    query: str,
    limit: int = 10,
    vector_weight: float = 0.7,
    entity_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining vector similarity and keyword matching.
    
    Args:
        query: Search query
        limit: Maximum number of results
        vector_weight: Weight for vector similarity (0-1)
        entity_type: Filter by entity type
    
    Returns:
        List of matching entities with combined scores
    """
    try:
        # Generate query embedding
        try:
            query_embedding = await generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for hybrid search: {e}")
            return []
        
        # Search
        results = await hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            limit=limit,
            vector_weight=vector_weight,
            entity_type=entity_type
        )
        
        # Format results and deduplicate
        seen_entities = set()
        formatted = []
        for result in results:
            entity_key = (result.node_name, result.node_type)  # Deduplicate by name and type
            if entity_key not in seen_entities:
                formatted.append({
                    "entity_id": str(result.entity_id),
                    "name": result.node_name,
                    "type": result.node_type,
                    "description": result.description or f"{result.node_name} is a {result.node_type} in the biomedical knowledge graph.",
                    "score": round(result.combined_score, 3) if result.combined_score else 0
                })
                seen_entities.add(entity_key)
        
        logger.info(f"Hybrid search for '{query}' returned {len(formatted)} results")
        # Limit results to prevent context overload
        return formatted[:8]
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        return []


async def get_document_tool(entity_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete information about a specific entity.
    
    Args:
        entity_id: UUID of the entity
    
    Returns:
        Entity information or None
    """
    try:
        entity = await get_entity_by_id(UUID(entity_id))
        
        if entity:
            return {
                "id": str(entity.id),
                "name": entity.node_name,
                "type": entity.node_type,
                "description": entity.description or "No description available",
                "source": entity.source,
                "metadata": entity.metadata
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        return None


async def list_documents_tool(
    limit: int = 20,
    offset: int = 0,
    entity_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List available entities with pagination.
    
    Args:
        limit: Maximum number of entities
        offset: Number of entities to skip
        entity_type: Filter by entity type
    
    Returns:
        List of entity metadata
    """
    try:
        entities = await list_entities(
            limit=limit,
            offset=offset,
            entity_type=entity_type
        )
        
        formatted = []
        for entity in entities:
            formatted.append({
                "id": str(entity.id),
                "name": entity.node_name,
                "type": entity.node_type,
                "description": (entity.description[:200] + "...") if entity.description and len(entity.description) > 200 else entity.description
            })
        
        return formatted
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        return []


async def get_entity_relationships_tool(
    entity_name: str,
    depth: int = 2
) -> Dict[str, Any]:
    """
    Get relationships for an entity from both database and knowledge graph.
    
    Args:
        entity_name: Name of the entity
        depth: Maximum traversal depth
    
    Returns:
        Entity relationships
    """
    try:
        # Try to get from Graphiti first
        try:
            graph_results = await get_entity_relationships(entity_name, depth=depth)
        except Exception as e:
            logger.warning(f"Failed to get graph relationships for '{entity_name}': {e}")
            graph_results = {"relationships": []}
        
        # Also get from database
        try:
            db_results = await get_entity_relationships_db(entity_name)
        except Exception as e:
            logger.warning(f"Failed to get database relationships for '{entity_name}': {e}")
            db_results = []
        
        return {
            "entity": entity_name,
            "graph_relationships": graph_results.get("relationships", []),
            "database_relationships": db_results,
            "depth": depth
        }
        
    except Exception as e:
        logger.error(f"Get entity relationships failed: {e}")
        return {"entity": entity_name, "graph_relationships": [], "database_relationships": [], "depth": depth}


async def get_entity_timeline_tool(
    entity_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get timeline of facts for an entity.
    
    Args:
        entity_name: Name of the entity
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    
    Returns:
        Timeline of facts
    """
    try:
        from agent.graph_utils import get_graphiti_client
        from datetime import datetime
        
        client = await get_graphiti_client()
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        results = await client.get_entity_timeline(entity_name, start, end)
        
        return results
        
    except Exception as e:
        logger.error(f"Get entity timeline failed: {e}")
        return []
