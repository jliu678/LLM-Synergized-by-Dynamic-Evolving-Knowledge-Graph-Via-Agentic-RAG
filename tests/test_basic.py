"""
Basic tests for the PrimeKG RAG system.
Run with: pytest tests/
"""

import pytest
import asyncio
from uuid import uuid4


@pytest.fixture
def sample_entity_data():
    """Sample entity data for testing."""
    return {
        "node_index": 1,
        "node_id": "MONDO:0004975",
        "node_name": "Alzheimer disease",
        "node_type": "disease",
        "description": "A neurodegenerative disease characterized by progressive dementia",
        "source": "PrimeKG"
    }


@pytest.fixture
def sample_relationship_data():
    """Sample relationship data for testing."""
    return {
        "source_id": "MONDO:0004975",
        "target_id": "DRUGBANK:DB00843",
        "relation_type": "treats",
        "display_relation": "treats",
        "source_type": "disease",
        "target_type": "drug"
    }


class TestModels:
    """Test Pydantic models."""
    
    def test_entity_model(self, sample_entity_data):
        """Test Entity model creation."""
        from agent.models import Entity
        
        entity = Entity(**sample_entity_data)
        assert entity.node_name == "Alzheimer disease"
        assert entity.node_type == "disease"
    
    def test_chat_request_model(self):
        """Test ChatRequest model."""
        from agent.models import ChatRequest
        
        request = ChatRequest(message="What is Alzheimer's disease?")
        assert request.message == "What is Alzheimer's disease?"
        assert request.session_id is None


class TestProviders:
    """Test LLM provider configuration."""
    
    def test_get_llm_model(self):
        """Test LLM model configuration."""
        from agent.providers import get_llm_model
        
        model = get_llm_model()
        assert isinstance(model, str)
        assert ":" in model  # Should be in format "provider:model"
    
    def test_get_embedding_model(self):
        """Test embedding model configuration."""
        from agent.providers import get_embedding_model
        
        model = get_embedding_model()
        assert isinstance(model, str)
        assert len(model) > 0


class TestDataLoader:
    """Test PrimeKG data loader."""
    
    def test_loader_initialization(self):
        """Test loader can be initialized."""
        from ingestion.data_loader import PrimeKGLoader
        
        loader = PrimeKGLoader("./test_data")
        assert loader.data_dir.name == "test_data"
    
    def test_entity_extraction(self):
        """Test entity extraction from mock data."""
        import pandas as pd
        from ingestion.data_loader import PrimeKGLoader
        
        # Create mock KG data
        mock_data = pd.DataFrame({
            'x_index': [1, 2],
            'x_id': ['A', 'B'],
            'x_name': ['Entity A', 'Entity B'],
            'x_type': ['disease', 'drug'],
            'y_index': [3, 4],
            'y_id': ['C', 'D'],
            'y_name': ['Entity C', 'Entity D'],
            'y_type': ['protein', 'pathway'],
            'relation': ['interacts', 'regulates'],
            'display_relation': ['interacts with', 'regulates']
        })
        
        loader = PrimeKGLoader()
        entities = loader.extract_entities(mock_data)
        
        assert len(entities) == 4  # 2 x entities + 2 y entities
        assert 'node_name' in entities.columns


@pytest.mark.asyncio
class TestEmbedder:
    """Test embedding generation."""
    
    async def test_embedder_initialization(self):
        """Test embedder can be initialized."""
        from ingestion.embedder import Embedder
        
        embedder = Embedder()
        assert embedder.model is not None
        assert embedder.batch_size > 0
    
    async def test_empty_text_handling(self):
        """Test handling of empty text."""
        from ingestion.embedder import Embedder
        
        embedder = Embedder()
        # Should return zero vector for empty text
        embedding = await embedder.generate_embedding("")
        assert len(embedding) > 0
        assert all(x == 0.0 for x in embedding)


@pytest.mark.asyncio
class TestDatabaseUtils:
    """Test database utilities (requires database connection)."""
    
    @pytest.mark.skip(reason="Requires database connection")
    async def test_pool_creation(self):
        """Test database pool creation."""
        from agent.db_utils import get_pool, close_pool
        
        pool = await get_pool()
        assert pool is not None
        
        await close_pool()


class TestTools:
    """Test agent tools (unit tests without actual calls)."""
    
    def test_tool_imports(self):
        """Test that all tools can be imported."""
        from agent.tools import (
            vector_search_tool,
            graph_search_tool,
            hybrid_search_tool,
            get_document_tool,
            list_documents_tool,
            get_entity_relationships_tool,
            get_entity_timeline_tool
        )
        
        # All tools should be callable
        assert callable(vector_search_tool)
        assert callable(graph_search_tool)
        assert callable(hybrid_search_tool)


class TestAgent:
    """Test main agent."""
    
    def test_agent_initialization(self):
        """Test agent can be imported and initialized."""
        from agent.agent import rag_agent, AgentDependencies
        
        assert rag_agent is not None
        
        # Test dependencies creation
        deps = AgentDependencies(session_id=str(uuid4()))
        assert deps.session_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
