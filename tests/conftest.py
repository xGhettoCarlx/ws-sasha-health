"""Shared fixtures for pytest."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """HTTPX async client for FastAPI TestClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_data_dir(tmp_path):
    """Temporary directory for test data files."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def sample_md_files(test_data_dir):
    """Create sample markdown files in test_data_dir."""
    files = {
        "sample1.md": "# Sample 1\n\nHello world.",
        "sample2.md": "# Sample 2\n\n## Section\n\nContent here.",
    }
    for name, content in files.items():
        (test_data_dir / name).write_text(content)
    return test_data_dir
