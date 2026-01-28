"""
Graphiti integration for temporal knowledge graph management.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Iterable
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Global Graphiti client
_graphiti_client = None


class GraphitiClient:
    """Manages Graphiti knowledge graph operations."""
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        use_ingestion_config: bool = False
    ):
        """Initialize Graphiti client."""
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        self.use_ingestion_config = use_ingestion_config
        
        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD environment variable not set")
        
        self.graphiti = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Graphiti client with custom OpenAI-compatible clients."""
        if self._initialized:
            return
        
        try:
            from graphiti_core import Graphiti
            from graphiti_core.llm_client import OpenAIClient, LLMConfig
            from graphiti_core.embedder import OpenAIEmbedder
            from .providers import get_llm_client, get_embedding_client, get_llm_model, get_embedding_model, get_ingestion_llm_model, get_embedding_provider
            
            # Get OpenAI-compatible clients
            llm_client = get_llm_client()
            embedding_client = get_embedding_client()
            
            # Extract model names
            if self.use_ingestion_config:
                llm_model = get_ingestion_llm_model().split(":")[-1]
                logger.info(f"Using Ingestion LLM: {llm_model}")
            else:
                llm_model = get_llm_model().split(":")[-1]
            
            embedding_model = get_embedding_model()
            embedding_provider = get_embedding_provider()
            
            # Create Graphiti LLM client
            llm_config = LLMConfig(model=llm_model, api_key="dummy")
            graphiti_llm = OpenAIClient(config=llm_config, client=llm_client, cache=False)

            # Handle different embedding providers
            logger.info(f"Embedding provider: {embedding_provider}")
            logger.info(f"Embedding client type: {type(embedding_client)}")
            
            if embedding_provider == "local" or embedding_client is None:
                # For local embeddings, we need to create a compatible client
                # Graphiti expects OpenAI-compatible interface
                logger.info("Attempting to initialize local embeddings...")
                try:
                    from ingestion.embedder import generate_embedding
                    from graphiti_core.embedder.client import EmbedderClient
                    
                    # Create a custom embedder class that inherits from EmbedderClient
                    class LocalGraphitiEmbedder(EmbedderClient):
                        def __init__(self, embedder_func, model_name):
                            self.embedder_func = embedder_func
                            self.model_name = model_name
                        
                        async def create(
                            self, 
                            input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
                        ) -> list[float]:
                            # Handle different input types
                            if isinstance(input_data, str):
                                texts = [input_data]
                            elif isinstance(input_data, list) and all(isinstance(x, str) for x in input_data):
                                texts = input_data
                            else:
                                # Convert other types to strings
                                texts = [str(input_data)] if not isinstance(input_data, list) else [str(x) for x in input_data]
                            
                            # Generate embeddings using local function
                            embeddings = []
                            for text in texts:
                                embedding = await self.embedder_func(text)
                                embeddings.append(embedding)
                            
                            # Return first embedding if single input, or list if multiple
                            return embeddings[0] if len(embeddings) == 1 else embeddings
                        
                        async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
                            # Generate embeddings for batch
                            embeddings = []
                            for text in input_data_list:
                                embedding = await self.embedder_func(text)
                                embeddings.append(embedding)
                            return embeddings
                    
                    # Use our custom embedder that inherits from EmbedderClient
                    graphiti_embedder = LocalGraphitiEmbedder(generate_embedding, embedding_model)
                    logger.info(f"Successfully created custom local embedder with model: {embedding_model}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize local embeddings: {e}")
                    # Fallback: disable Graphiti search
                    self.graphiti = None
                    self._initialized = True
                    logger.warning("Graphiti disabled due to embedding initialization failure")
                    return
            else:
                # Use OpenAI embeddings
                logger.info(f"Using OpenAI embeddings with client type: {type(embedding_client)}")
                graphiti_embedder = OpenAIEmbedder(embedding_client, embedding_model)
                logger.info(f"Using OpenAI embeddings with model: {embedding_model}")
            
            # Initialize Graphiti
            self.graphiti = Graphiti(
                self.neo4j_uri,
                self.neo4j_user,
                self.neo4j_password,
                llm_client=graphiti_llm,
                embedder=graphiti_embedder
            )
            
            await self.graphiti.build_indices_and_constraints()
            self._initialized = True
            logger.info("Graphiti client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    async def close(self):
        """Close Graphiti connection."""
        if self.graphiti:
            await self.graphiti.close()
            self._initialized = False
            logger.info("Graphiti client closed")
    
    async def add_episode(
        self,
        episode_id: str,
        content: str,
        source: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add an episode to the knowledge graph."""
        if not self._initialized:
            await self.initialize()
        
        try:
            episode_time = timestamp or datetime.now(timezone.utc)
            
            await self.graphiti.add_episode(
                name=episode_id,
                episode_body=content,
                source_description=source,
                reference_time=episode_time
            )
            
            logger.debug(f"Added episode: {episode_id}")
            
        except Exception as e:
            logger.error(f"Failed to add episode {episode_id}: {e}")
            raise
    
    async def search(
        self,
        query: str,
        center_node_distance: int = 2,
        use_hybrid_search: bool = True
    ) -> List[Dict[str, Any]]:
        """Search the knowledge graph."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Use the correct Graphiti search API
            # The search method expects: query, center_node_uuid, group_ids, num_results
            results = await self.graphiti.search(
                query=query,
                center_node_uuid=None,  # Optional center node
                group_ids=None,         # Search all groups
                num_results=8           # Limit results
            )
            
            # Handle case where results might be None or empty
            if not results:
                return []
            
            # Format EntityEdge objects to dictionaries
            formatted_results = []
            for result in results:
                try:
                    # Handle EntityEdge objects
                    if hasattr(result, 'fact'):
                        formatted_results.append({
                            "fact": result.fact,
                            "episode_ids": getattr(result, 'episode_ids', []),
                            "valid_at": getattr(result, 'valid_at', None),
                            "invalid_at": getattr(result, 'invalid_at', None)
                        })
                    elif hasattr(result, 'source') and hasattr(result, 'target'):
                        # Handle edge objects with source/target
                        formatted_results.append({
                            "fact": f"{result.source} -> {result.target}",
                            "episode_ids": getattr(result, 'episode_ids', []),
                            "valid_at": getattr(result, 'valid_at', None),
                            "invalid_at": getattr(result, 'invalid_at', None)
                        })
                    else:
                        # Handle other object types
                        formatted_results.append({
                            "fact": str(result),
                            "episode_ids": getattr(result, 'episode_ids', []),
                            "valid_at": getattr(result, 'valid_at', None),
                            "invalid_at": getattr(result, 'invalid_at', None)
                        })
                except Exception as e:
                    logger.warning(f"Failed to format search result: {e}, result type: {type(result)}")
                    continue
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search knowledge graph: {e}", exc_info=True)
            return []
    
    async def get_related_entities(
        self,
        entity_name: str,
        relationship_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """Get entities related to a given entity using Graphiti search."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Use Graphiti search to find related entities
            query = f"What is related to {entity_name}?"
            results = await self.search(query, center_node_distance=depth)
            
            return {
                "entity": entity_name,
                "relationships": results,
                "depth": depth
            }
            
        except Exception as e:
            logger.error(f"Failed to get related entities for {entity_name}: {e}")
            return {"entity": entity_name, "relationships": [], "depth": depth}
    
    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get timeline of facts for an entity."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Search for temporal information about the entity
            query = f"Timeline and history of {entity_name}"
            results = await self.search(query)
            
            # Filter by date range if provided
            if start_date or end_date:
                filtered_results = []
                for result in results:
                    valid_at = result.get("valid_at")
                    if valid_at:
                        if start_date and valid_at < start_date:
                            continue
                        if end_date and valid_at > end_date:
                            continue
                    filtered_results.append(result)
                return filtered_results
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get timeline for {entity_name}: {e}")
            return []
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the knowledge graph."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # This would require custom Cypher queries
            # For now, return basic info
            return {
                "status": "connected",
                "uri": self.neo4j_uri
            }
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {"status": "error", "message": str(e)}
    
    async def clear_graph(self):
        """Clear all data from the graph (USE WITH CAUTION)."""
        if not self._initialized:
            await self.initialize()
        
        logger.warning("Clearing all data from knowledge graph")
        # Graphiti doesn't have a built-in clear method, would need custom implementation
        # For now, just log the warning
        pass

# Global client instance
async def get_graphiti_client(for_ingestion: bool = False) -> GraphitiClient:
    """Get or create the global Graphiti client."""
    global _graphiti_client
    try:
        if _graphiti_client is None:
            _graphiti_client = GraphitiClient(use_ingestion_config=for_ingestion)
            await _graphiti_client.initialize()
        return _graphiti_client
    except Exception as e:
        logger.error(f"Failed to get or initialize Graphiti client: {e}")
        raise


async def close_graphiti():
    """Close the global Graphiti client."""
    global _graphiti_client
    if _graphiti_client:
        await _graphiti_client.close()
        _graphiti_client = None


# Convenience functions
async def add_to_knowledge_graph(
    content: str,
    source: str,
    episode_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Add content to the knowledge graph."""
    client = await get_graphiti_client()
    
    if not episode_id:
        import uuid
        episode_id = str(uuid.uuid4())
    
    await client.add_episode(episode_id, content, source, metadata=metadata)
    return episode_id


async def search_knowledge_graph(query: str) -> List[Dict[str, Any]]:
    """Search the knowledge graph."""
    client = await get_graphiti_client()
    return await client.search(query)


async def get_entity_relationships(entity: str, depth: int = 2) -> Dict[str, Any]:
    """Get relationships for an entity."""
    try:
        client = await get_graphiti_client()
        return await client.get_related_entities(entity, depth=depth)
    except Exception as e:
        logger.error(f"Failed to get entity relationships for '{entity}': {e}")
        return {"entity": entity, "relationships": [], "depth": depth}


async def get_graph_statistics() -> Dict[str, Any]:
    """Get basic statistics about the knowledge graph."""
    client = await get_graphiti_client()
    return await client.get_graph_statistics()
