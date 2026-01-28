"""
Main Pydantic AI agent for biomedical knowledge retrieval.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings

from .providers import get_llm_model
from .prompts import SYSTEM_PROMPT
from .tools import (
    vector_search_tool,
    graph_search_tool,
    hybrid_search_tool,
    get_document_tool,
    list_documents_tool,
    get_entity_relationships_tool,
    get_entity_timeline_tool
)

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies for the agent."""
    session_id: str
    user_id: Optional[str] = None
    search_preferences: Optional[Dict[str, Any]] = None



# Define tool functions with explicit Tool instances for retry configuration
async def vector_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10
) -> list:
    """
    Search for biomedical entities using semantic similarity.
    
    This tool performs vector similarity search across entity descriptions
    to find semantically related content. Best for finding entities by
    symptoms, mechanisms, treatments, or characteristics.
    
    Args:
        query: Search query describing what to find
        limit: Maximum number of results (default 10)
    
    Returns:
        List of matching entities with similarity scores
    """
    return await vector_search_tool(query, limit)


async def graph_search(
    ctx: RunContext[AgentDependencies],
    query: str
) -> list:
    """
    Search the knowledge graph for facts and relationships.
    
    This tool queries the Graphiti knowledge graph to find specific facts,
    relationships between entities, and temporal information. Best for
    finding connections and historical data.
    
    Args:
        query: Search query to find facts and relationships
    
    Returns:
        List of facts with temporal data
    """
    return await graph_search_tool(query)


async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10,
    vector_weight: float = 0.7
) -> list:
    """
    Perform combined vector and keyword search.
    
    This tool combines semantic similarity with keyword matching for
    comprehensive results. Best for broad exploratory queries.
    
    Args:
        query: Search query
        limit: Maximum number of results (default 10)
        vector_weight: Weight for vector similarity 0-1 (default 0.7)
    
    Returns:
        List of entities ranked by combined score
    """
    return await hybrid_search_tool(query, limit, vector_weight)


async def get_document(
    ctx: RunContext[AgentDependencies],
    entity_id: str
) -> dict:
    """
    Retrieve complete information about a specific entity.
    
    Use this when you have an entity ID and need full details.
    
    Args:
        entity_id: UUID of the entity
    
    Returns:
        Complete entity data or None if not found
    """
    return await get_document_tool(entity_id)


async def list_documents(
    ctx: RunContext[AgentDependencies],
    limit: int = 20,
    offset: int = 0
) -> list:
    """
    List available entities with pagination.
    
    Browse entities in the knowledge base. Useful for exploration.
    
    Args:
        limit: Maximum number of entities (default 20)
        offset: Number to skip for pagination (default 0)
    
    Returns:
        List of entity metadata
    """
    return await list_documents_tool(limit, offset)


async def get_entity_relationships(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    depth: int = 2
) -> dict:
    """
    Get all relationships for a specific entity.
    
    Explores how an entity (disease, drug, protein, etc.) relates to
    other entities. Best for questions about connections like
    "what drugs treat X" or "what proteins are related to Y".
    
    Args:
        entity_name: Name of the entity
        depth: Maximum traversal depth (default 2)
    
    Returns:
        Entity relationships from graph and database
    """
    return await get_entity_relationships_tool(entity_name, depth)


async def get_entity_timeline(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list:
    """
    Get chronological information about an entity.
    
    Retrieves temporal facts showing how information has evolved.
    Best for understanding historical context.
    
    Args:
        entity_name: Name of the entity
        start_date: Start date in ISO format (optional)
        end_date: End date in ISO format (optional)
    
    Returns:
        Chronological list of facts
    """
    return await get_entity_timeline_tool(entity_name, start_date, end_date)


# Configure model settings to prevent repetition
# Higher penalties = less repetition (0.0-2.0 range)
model_settings: ModelSettings = {
    "frequency_penalty": 1.2,  # Strong penalty for frequent tokens (0.0-2.0) - increased to prevent loops
    "presence_penalty": 1.0,   # Strong penalty for tokens that have appeared (0.0-2.0) - increased
    "max_tokens": 1500,        # Limit response length to prevent infinite generation
    "temperature": 0.7,        # Balanced creativity (0.0-2.0)
}

# Initialize the agent with tools configured with max_retries=3 and repetition prevention
rag_agent = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT,
    model_settings=model_settings,
    tools=[
        Tool(vector_search, max_retries=3),
        Tool(graph_search, max_retries=3),
        Tool(hybrid_search, max_retries=3),
        Tool(get_document, max_retries=3),
        Tool(list_documents, max_retries=3),
        Tool(get_entity_relationships, max_retries=3),
        Tool(get_entity_timeline, max_retries=3),
    ]
)
