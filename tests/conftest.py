"""
Pytest configuration and fixtures.
"""

import pytest
import os
from pathlib import Path


def pytest_configure(config):
    """Configure pytest."""
    # Set test environment
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "WARNING"


@pytest.fixture(scope="session")
def test_data_dir():
    """Create and return test data directory."""
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def sample_entities():
    """Sample entities for testing."""
    return [
        {
            "node_index": 1,
            "node_id": "MONDO:0004975",
            "node_name": "Alzheimer disease",
            "node_type": "disease"
        },
        {
            "node_index": 2,
            "node_id": "DRUGBANK:DB00843",
            "node_name": "Donepezil",
            "node_type": "drug"
        },
        {
            "node_index": 3,
            "node_id": "UNIPROT:P12345",
            "node_name": "APOE",
            "node_type": "protein"
        }
    ]
