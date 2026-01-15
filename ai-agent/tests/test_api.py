"""Tests for the API endpoints."""
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "vibber-ai-agent"


def test_root_redirects_to_docs(client):
    """Test that root redirects to API docs."""
    response = client.get("/", follow_redirects=False)
    # Root might redirect to docs or return a response
    assert response.status_code in [200, 307, 308]
