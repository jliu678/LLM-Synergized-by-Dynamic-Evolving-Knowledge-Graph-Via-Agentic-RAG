"""
Embedding generation for PrimeKG entity descriptions.
"""

import os
import logging
from typing import List
import asyncio
from dotenv import load_dotenv

from agent.providers import get_embedding_client, get_embedding_model

load_dotenv()

logger = logging.getLogger(__name__)

# Global embedder instance to avoid reloading model
_global_embedder = None


class Embedder:
    """Generates embeddings for text descriptions."""
    
    def __init__(self):
        """Initialize embedder with configured client."""
        self.model_name = get_embedding_model()
        self.client = get_embedding_client()
        self.batch_size = 100
        
        # Initialize local model if no client (implies local provider)
        self.local_model = None
        if not self.client:
            logger.info(f"Initializing local embedding model: {self.model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                # Use CPU by default, or CUDA if available
                device = "cpu"
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                
                self.local_model = SentenceTransformer(self.model_name, device=device)
                logger.info(f"Local model initialized on {device}")
            except ImportError:
                raise ImportError("sentence-transformers not installed. Run 'pip install sentence-transformers'")
            except Exception as e:
                logger.error(f"Failed to load local model: {e}")
                raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            # Return zero vector for empty text
            dim = 1024 if "bge-m3" in self.model_name else 1536
            return [0.0] * dim
        
        try:
            if self.local_model:
                # Run in thread pool to avoid blocking async loop
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, 
                    lambda: self.local_model.encode(text, normalize_embeddings=True)
                )
                return embedding.tolist()
            else:
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        if not texts:
            return []
        
        # Filter out empty texts but remember their positions
        text_map = {}
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                text_map[len(valid_texts)] = i
                valid_texts.append(text)
        
        if not valid_texts:
            # All texts were empty
            return [[0.0] * 1536 for _ in texts]
        
        try:
            # Process in batches
            all_embeddings = [None] * len(texts)
            
            if self.local_model:
                # Use local model for batch processing
                loop = asyncio.get_event_loop()
                valid_embeddings = await loop.run_in_executor(
                    None, 
                    lambda: self.local_model.encode(valid_texts, normalize_embeddings=True).tolist()
                )
                
                # Map back
                for i, emb in enumerate(valid_embeddings):
                    original_idx = text_map[i]
                    all_embeddings[original_idx] = emb
                    
            else:
                for i in range(0, len(valid_texts), self.batch_size):
                    batch = valid_texts[i:i + self.batch_size]
                    
                    response = await self.client.embeddings.create(
                        model=self.model_name,
                        input=batch
                    )
                    
                    # Map embeddings back to original positions
                    for j, embedding_data in enumerate(response.data):
                        original_idx = text_map[i + j]
                        all_embeddings[original_idx] = embedding_data.embedding
                    
                    # Small delay to avoid rate limits
                    if i + self.batch_size < len(valid_texts):
                        await asyncio.sleep(0.1)
            
            # Fill in zero vectors for empty texts
            for i, emb in enumerate(all_embeddings):
                if emb is None:
                    all_embeddings[i] = [0.0] * 1536
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise


async def generate_embedding(text: str) -> List[float]:
    """Convenience function to generate a single embedding."""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = Embedder()
    return await _global_embedder.generate_embedding(text)


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Convenience function to generate multiple embeddings."""
    embedder = Embedder()
    return await embedder.generate_embeddings_batch(texts)
