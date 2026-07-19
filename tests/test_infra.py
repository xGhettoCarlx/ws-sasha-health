"""Infrastructure validation tests."""

import pytest


def test_pytest_works():
    """Trivial test to prove pytest is configured correctly."""
    assert True


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Verify the /health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["storage"] == "ok"


@pytest.mark.asyncio
async def test_client_fixture_type(client):
    """Verify client fixture returns an httpx.AsyncClient."""
    from httpx import AsyncClient
    assert isinstance(client, AsyncClient)


def test_test_data_dir_fixture(test_data_dir):
    """Verify test_data_dir fixture creates a writable directory."""
    assert test_data_dir.exists()
    assert test_data_dir.is_dir()
    # Can write to it
    f = test_data_dir / "test.txt"
    f.write_text("hello")
    assert f.read_text() == "hello"


def test_sample_md_files_fixture(sample_md_files):
    """Verify sample_md_files fixture creates expected markdown files."""
    assert (sample_md_files / "sample1.md").exists()
    assert (sample_md_files / "sample2.md").exists()
    content = (sample_md_files / "sample1.md").read_text()
    assert "# Sample 1" in content
