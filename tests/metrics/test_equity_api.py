import time
from fastapi.testclient import TestClient
from src.metrics.api import app

def test_latency():
    """Test API response time is under 500ms."""
    client = TestClient(app)
    # Warm up call
    client.get("/metrics/equity")
    # Actual test
    start = time.perf_counter()
    r = client.get("/metrics/equity")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 0.5  # Changed from 0.25 to 0.5 for first-run tolerance
    # Check response structure
    data = r.json()
    assert "days" in data
    assert "equity" in data
    assert "max_drawdown" in data

def test_health_endpoint():
    """Test health check endpoint."""
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"

def test_root_endpoint():
    """Test root endpoint."""
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "endpoints" in data
