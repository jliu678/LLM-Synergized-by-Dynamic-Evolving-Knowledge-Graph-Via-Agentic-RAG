"""
PostgreSQL database utilities for PrimeKG entities and embeddings.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import asyncpg
from dotenv import load_dotenv

from .models import Entity, EntityEmbedding, Relationship, SearchResult, Session, Message

load_dotenv()

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool created")
    
    return _pool


async def close_pool():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


# ============================================================================
# ENTITY OPERATIONS
# ============================================================================

async def insert_entity(entity: Entity) -> UUID:
    """Insert a new entity into the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO entities (node_index, node_id, node_name, node_type, description, source, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (node_id) DO UPDATE
            SET node_name = EXCLUDED.node_name,
                description = EXCLUDED.description,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            entity.node_index,
            entity.node_id,
            entity.node_name,
            entity.node_type,
            entity.description,
            entity.source,
            entity.metadata
        )
        return row["id"]


async def insert_entity_embedding(embedding: EntityEmbedding) -> UUID:
    """Insert an entity embedding."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO entity_embeddings (entity_id, embedding, embedding_model)
            VALUES ($1, $2::vector, $3)
            ON CONFLICT (entity_id, embedding_model) DO UPDATE
            SET embedding = EXCLUDED.embedding
            RETURNING id
            """,
            embedding.entity_id,
            str(embedding.embedding),  # Convert list to string for vector type
            embedding.embedding_model
        )
        return row["id"]


async def insert_relationship(relationship: Relationship) -> UUID:
    """Insert a relationship between entities."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO relationships (
                source_entity_id, target_entity_id, relation_type,
                display_relation, source_type, target_type, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (source_entity_id, target_entity_id, relation_type) DO NOTHING
            RETURNING id
            """,
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship.relation_type,
            relationship.display_relation,
            relationship.source_type,
            relationship.target_type,
            relationship.metadata
        )
        return row["id"] if row else None


# ============================================================================
# SEARCH OPERATIONS
# ============================================================================

async def vector_search(
    query_embedding: List[float],
    limit: int = 10,
    threshold: float = 0.5,
    entity_type: Optional[str] = None
) -> List[SearchResult]:
    """Perform vector similarity search."""
    try:
        pool = await get_pool()
    except Exception as e:
        logger.error(f"Failed to get database pool for vector search: {e}")
        return []
    
    try:
        # Convert embedding list to PostgreSQL vector string format
        # Format: '[1.0,2.0,3.0]' (no spaces after commas)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM search_entities_by_vector($1::vector, $2, $3, $4)
                """,
                embedding_str,
                threshold,
                limit,
                entity_type
            )
        
        return [
            SearchResult(
                entity_id=row["entity_id"],
                node_name=row["node_name"],
                node_type=row["node_type"],
                description=row["description"],
                similarity=row["similarity"]
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Vector search query failed: {e}")
        return []


async def hybrid_search(
    query_embedding: List[float],
    query_text: str,
    limit: int = 10,
    vector_weight: float = 0.7,
    entity_type: Optional[str] = None
) -> List[SearchResult]:
    """Perform hybrid search (vector + keyword)."""
    try:
        pool = await get_pool()
    except Exception as e:
        logger.error(f"Failed to get database pool for hybrid search: {e}")
        return []
    
    try:
        # Convert embedding list to PostgreSQL vector string format
        # Format: '[1.0,2.0,3.0]' (no spaces after commas)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM search_entities_hybrid($1::vector, $2, $3, $4, $5)
                """,
                embedding_str,
                query_text,
                limit,
                vector_weight,
                entity_type
            )
        
        return [
            SearchResult(
                entity_id=row["entity_id"],
                node_name=row["node_name"],
                node_type=row["node_type"],
                description=row["description"],
                combined_score=row["combined_score"]
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Hybrid search query failed: {e}")
        return []


async def get_entity_by_id(entity_id: UUID) -> Optional[Entity]:
    """Get an entity by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM entities WHERE id = $1
            """,
            entity_id
        )
        
        if row:
            return Entity(**dict(row))
        return None


async def get_entity_by_node_id(node_id: str) -> Optional[Entity]:
    """Get an entity by PrimeKG node ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM entities WHERE node_id = $1
            """,
            node_id
        )
        
        if row:
            return Entity(**dict(row))
        return None


async def list_entities(
    limit: int = 20,
    offset: int = 0,
    entity_type: Optional[str] = None
) -> List[Entity]:
    """List entities with pagination."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if entity_type:
            rows = await conn.fetch(
                """
                SELECT * FROM entities
                WHERE node_type = $1
                ORDER BY node_name
                LIMIT $2 OFFSET $3
                """,
                entity_type,
                limit,
                offset
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM entities
                ORDER BY node_name
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset
            )
        
        return [Entity(**dict(row)) for row in rows]


async def get_entity_relationships_db(node_id: str) -> List[Dict[str, Any]]:
    """Get relationships for an entity from database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM get_entity_relationships($1, 1)
            """,
            node_id
        )
        
        return [dict(row) for row in rows]


# ============================================================================
# SESSION OPERATIONS
# ============================================================================

async def create_session(user_id: Optional[str] = None) -> UUID:
    """Create a new conversation session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id)
            VALUES ($1)
            RETURNING id
            """,
            user_id
        )
        return row["id"]


async def get_session(session_id: UUID) -> Optional[Session]:
    """Get a session by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM sessions WHERE id = $1
            """,
            session_id
        )
        
        if row:
            return Session(**dict(row))
        return None


async def add_message(
    session_id: UUID,
    role: str,
    content: str,
    tool_calls: Optional[List[Dict[str, Any]]] = None
) -> UUID:
    """Add a message to a session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (session_id, role, content, tool_calls)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            session_id,
            role,
            content,
            tool_calls
        )
        return row["id"]


async def get_session_messages(
    session_id: UUID,
    limit: int = 50
) -> List[Message]:
    """Get messages for a session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM messages
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_id,
            limit
        )
        
        return [Message(**dict(row)) for row in reversed(rows)]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def get_entity_count() -> int:
    """Get total number of entities."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as count FROM entities")
        return row["count"]


async def get_entity_types() -> List[Tuple[str, int]]:
    """Get entity types and their counts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT node_type, COUNT(*) as count
            FROM entities
            GROUP BY node_type
            ORDER BY count DESC
            """
        )
        return [(row["node_type"], row["count"]) for row in rows]
