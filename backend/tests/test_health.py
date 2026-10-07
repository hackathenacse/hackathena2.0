from fastapi.testclient import TestClient


def test_health_check_endpoint(test_client: TestClient):
    """Verifies that GET /api/health returns HTTP 200 with status: ok."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "ffmpeg_available" in data
    assert "ffprobe_available" in data
    assert "version" in data
    assert data["ffmpeg_available"] is True
    assert data["ffprobe_available"] is True
