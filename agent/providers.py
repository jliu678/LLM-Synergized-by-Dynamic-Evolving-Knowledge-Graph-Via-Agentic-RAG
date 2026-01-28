"""
LLM provider abstraction for flexible model support.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Map custom env vars to standard ones for libraries that expect them
if os.getenv("LLM_API_KEY") and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("LLM_API_KEY")

if os.getenv("LLM_BASE_URL") and not os.getenv("OPENAI_BASE_URL"):
    os.environ["OPENAI_BASE_URL"] = os.getenv("LLM_BASE_URL")


def get_llm_provider() -> str:
    """Get the configured LLM provider."""
    return os.getenv("LLM_PROVIDER", "openai")


def get_llm_model() -> str:
    """
    Get the LLM model configuration for Pydantic AI.
    Returns model string in format: provider:model_name
    """
    provider = get_llm_provider()
    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model_choice = os.getenv("LLM_CHOICE", "gpt-4o-mini")
    
    if provider == "openai":
        return f"openai:{model_choice}"
    elif provider == "ollama":
        # Pydantic AI supports Ollama through OpenAI-compatible interface
        return f"openai:{model_choice}"
    elif provider == "openrouter":
        return f"openai:{model_choice}"
    elif provider == "gemini":
        return f"gemini-1.5-flash"  # Pydantic AI has native Gemini support
    else:
        # Default to OpenAI
        return f"openai:{model_choice}"


def get_ingestion_llm_model() -> str:
    """
    Get the LLM model for ingestion tasks (can be different/faster).
    """
    ingestion_choice = os.getenv("INGESTION_LLM_CHOICE")
    if ingestion_choice:
        provider = get_llm_provider()
        return f"{provider}:{ingestion_choice}"
    return get_llm_model()


def get_embedding_provider() -> str:
    """Get the configured embedding provider."""
    return os.getenv("EMBEDDING_PROVIDER", "openai")


def get_embedding_model() -> str:
    """Get the embedding model name."""
    return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def get_embedding_dimension() -> int:
    """Get the embedding dimension based on the model."""
    dimension = os.getenv("VECTOR_DIMENSION")
    if dimension:
        return int(dimension)
    
    # Default dimensions for common models
    model = get_embedding_model()
    if "text-embedding-3-small" in model:
        return 1536
    elif "text-embedding-3-large" in model:
        return 3072
    elif "nomic-embed-text" in model:
        return 768
    elif "bge-m3" in model:
        return 1024
    else:
        return 1536  # Default


def get_embedding_client():
    """
    Get an OpenAI-compatible client for embeddings.
    Returns None if using local provider.
    """
    provider = get_embedding_provider()
    
    if provider == "local":
        return None
        
    from openai import AsyncOpenAI
    
    base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("EMBEDDING_API_KEY")
    
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key
    )


def get_llm_client():
    """
    Get an OpenAI-compatible client for LLM calls.
    Used by Graphiti for knowledge graph operations.
    """
    from openai import AsyncOpenAI
    
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("LLM_API_KEY")
    
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key
    )
