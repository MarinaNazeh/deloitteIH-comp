"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def cache_dir(project_root):
    """Return the cache directory path."""
    return os.path.join(project_root, "cache")


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return the data directory path."""
    return os.path.join(project_root, "data")


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_cache: marks tests that require cache to exist"
    )
