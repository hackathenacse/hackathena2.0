import io
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_reject_invalid_file_extension(test_client: TestClient):
    """Rejects files with disallowed extensions (e.g., .txt, .exe, .pdf)."""
    fake_file = io.BytesIO(b"dummy text content")
    response = test_client.post(
        "/api/analyses",
        files={"file": ("malicious.exe", fake_file, "application/x-msdownload")}
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_reject_invalid_mime_type(test_client: TestClient):
    """Rejects files with disallowed MIME types even if named .mp4."""
    fake_file = io.BytesIO(b"fake data")
    response = test_client.post(
        "/api/analyses",
        files={"file": ("fake_video.mp4", fake_file, "image/png")}
    )
    assert response.status_code == 400
    assert "Unsupported MIME type" in response.json()["detail"]


def test_reject_empty_file(test_client: TestClient):
    """Rejects empty 0-byte uploads."""
    empty_file = io.BytesIO(b"")
    response = test_client.post(
        "/api/analyses",
        files={"file": ("empty.mp4", empty_file, "video/mp4")}
    )
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_reject_file_exceeding_max_size(test_client: TestClient, monkeypatch):
    """Rejects uploads that exceed the configured size limit."""
    # Temporarily set max size to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    
    # 2 MB buffer
    large_buffer = io.BytesIO(b"0" * (2 * 1024 * 1024))
    response = test_client.post(
        "/api/analyses",
        files={"file": ("large_video.mp4", large_buffer, "video/mp4")}
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"]
