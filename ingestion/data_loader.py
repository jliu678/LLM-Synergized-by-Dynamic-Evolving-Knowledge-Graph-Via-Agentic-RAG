"""
PrimeKG data loader - downloads and processes CSV files.
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import httpx
import random
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PrimeKGLoader:
    """Loads and processes PrimeKG CSV data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize loader with data directory."""
        self.data_dir = Path(data_dir or os.getenv("PRIMEKG_DATA_DIR", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.kg_file = self.data_dir / "kg.csv"
        self.drug_features_file = self.data_dir / "drug_features.csv"
        self.disease_features_file = self.data_dir / "disease_features.csv"
    
    async def download_primekg(self):
        """Download PrimeKG CSV files from Harvard Dataverse."""
        logger.info("Downloading PrimeKG data...")
        
        # Main KG file
        kg_url = "https://dataverse.harvard.edu/api/access/datafile/6180620"
        
        if not self.kg_file.exists():
            logger.info(f"Downloading kg.csv to {self.kg_file}")
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                response = await client.get(kg_url)
                response.raise_for_status()
                self.kg_file.write_bytes(response.content)
            logger.info("Downloaded kg.csv successfully")
        else:
            logger.info("kg.csv already exists, skipping download")
        
        # Note: drug_features.csv and disease_features.csv URLs would need to be added
        # For now, we'll work with just the main KG file
    
    def load_kg(self, limit: Optional[int] = None, random_sample: bool = False) -> pd.DataFrame:
        """Load the main knowledge graph CSV."""
        logger.info(f"Loading kg.csv...")
        
        if not self.kg_file.exists():
            raise FileNotFoundError(f"kg.csv not found at {self.kg_file}. Run with --download first.")
        
        df = pd.read_csv(self.kg_file, low_memory=False)
        
        if limit:
            if random_sample:
                # Random sampling
                if limit < len(df):
                    df = df.sample(n=limit, random_state=42)  # Fixed seed for reproducibility
                    logger.info(f"Loaded {len(df)} rows (random sample of {limit})")
                else:
                    df = df.head(limit)
                    logger.info(f"Loaded {len(df)} rows (limited to {limit})")
            else:
                # Take first N rows (default behavior)
                df = df.head(limit)
                logger.info(f"Loaded {len(df)} rows (first {limit})")
        else:
            logger.info(f"Loaded {len(df)} rows")
        
        return df
    
    def load_features(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Load drug and disease feature files if available."""
        drug_features = None
        disease_features = None
        
        if self.drug_features_file.exists():
            drug_features = pd.read_csv(self.drug_features_file)
            logger.info(f"Loaded {len(drug_features)} drug features")
        
        if self.disease_features_file.exists():
            disease_features = pd.read_csv(self.disease_features_file)
            logger.info(f"Loaded {len(disease_features)} disease features")
        
        return drug_features, disease_features
    
    def extract_entities(self, kg_df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique entities from the knowledge graph."""
        logger.info("Extracting entities...")
        
        # Get unique nodes from both x and y columns
        x_entities = kg_df[['x_index', 'x_id', 'x_name', 'x_type']].rename(
            columns={'x_index': 'node_index', 'x_id': 'node_id', 'x_name': 'node_name', 'x_type': 'node_type'}
        )
        
        y_entities = kg_df[['y_index', 'y_id', 'y_name', 'y_type']].rename(
            columns={'y_index': 'node_index', 'y_id': 'node_id', 'y_name': 'node_name', 'y_type': 'node_type'}
        )
        
        # Combine and deduplicate
        entities = pd.concat([x_entities, y_entities]).drop_duplicates(subset=['node_id'])
        
        logger.info(f"Extracted {len(entities)} unique entities")
        return entities
    
    def extract_relationships(self, kg_df: pd.DataFrame) -> pd.DataFrame:
        """Extract relationships from the knowledge graph."""
        logger.info("Extracting relationships...")
        
        relationships = kg_df[['x_id', 'y_id', 'relation', 'display_relation', 'x_type', 'y_type']].copy()
        relationships.columns = ['source_id', 'target_id', 'relation_type', 'display_relation', 'source_type', 'target_type']
        
        logger.info(f"Extracted {len(relationships)} relationships")
        return relationships


async def download_primekg_data(data_dir: str = "./data"):
    """Convenience function to download PrimeKG data."""
    loader = PrimeKGLoader(data_dir)
    await loader.download_primekg()


def load_primekg_data(data_dir: str = "./data", limit: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience function to load PrimeKG data."""
    loader = PrimeKGLoader(data_dir)
    kg_df = loader.load_kg(limit=limit)
    entities_df = loader.extract_entities(kg_df)
    relationships_df = loader.extract_relationships(kg_df)
    
    return entities_df, relationships_df
