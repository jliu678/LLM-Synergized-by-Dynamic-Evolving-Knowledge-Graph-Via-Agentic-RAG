"""
Data models for the agentic RAG system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    user_id: Optional[str] = Field(None, description="User identifier")


class ToolCall(BaseModel):
    """Model for tracking tool usage."""
    tool_name: str = Field(..., description="Name of the tool used")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    result_summary: Optional[str] = Field(None, description="Summary of tool result")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tools used in this response")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StreamChunk(BaseModel):
    """Model for streaming response chunks."""
    content: str = Field(..., description="Chunk content")
    done: bool = Field(default=False, description="Whether streaming is complete")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tools used (only in final chunk)")


class Entity(BaseModel):
    """Model for PrimeKG entity."""
    id: Optional[UUID] = None
    node_index: int
    node_id: str
    node_name: str
    node_type: str  # disease, drug, protein, etc.
    description: Optional[str] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityEmbedding(BaseModel):
    """Model for entity embedding."""
    id: Optional[UUID] = None
    entity_id: UUID
    embedding: List[float]
    embedding_model: str


class Relationship(BaseModel):
    """Model for PrimeKG relationship."""
    id: Optional[UUID] = None
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: str
    display_relation: Optional[str] = None
    source_type: Optional[str] = None
    target_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Model for search results."""
    entity_id: UUID
    node_name: str
    node_type: str
    description: Optional[str] = None
    similarity: Optional[float] = None
    combined_score: Optional[float] = None


class Session(BaseModel):
    """Model for conversation session."""
    id: Optional[UUID] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """Model for conversation message."""
    id: Optional[UUID] = None
    session_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None
