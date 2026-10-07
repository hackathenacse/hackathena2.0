from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.utils.hashing import compute_sha256


def test_post_analyses_end_to_end(test_client: TestClient, synthetic_video_path: Path):
    """
    End-to-end integration test for POST /api/analyses.
    Verifies:
      - Valid video upload processing
      - Accurate SHA-256 hashing
      - Video metadata extraction
      - Frame sampling count
      - Stage 1 contract adherence
      - Stage 2 synthesis (reliability, evidence, timeline, assessment, explanations, limitations)
      - Stage 3 fraud intent evaluation (handling silent/speechless video gracefully as NOT_ASSESSABLE)
      - Zero artifact leakage / guaranteed temp directory cleanup
    """
    expected_hash = compute_sha256(synthetic_video_path)

    with open(synthetic_video_path, "rb") as video_file:
        response = test_client.post(
            "/api/analyses",
            files={"file": (synthetic_video_path.name, video_file, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()

    # 1. Structure Verification
    assert "id" in data
    assert data["status"] == "completed"
    assert "created_at" in data

    # 2. Video Metadata Verification
    video = data["video"]
    assert video["filename"] == synthetic_video_path.name
    assert video["sha256"] == expected_hash
    assert video["duration_s"] == pytest.approx(3.0, rel=0.2)
    assert video["fps"] == pytest.approx(10.0, rel=0.1)
    assert video["width"] == 320
    assert video["height"] == 240
    assert video["frames_sampled"] >= 3

    # 3. Stage 1 Contract: Active VisualDetector + Unavailable Audio/Speech Placeholders
    visual = data["visual"]
    assert visual["available"] is True
    assert visual["status"] == "completed"
    assert visual["model"] == "EfficientNet-B0-FFPP-C23"
    assert visual["frames_analyzed"] >= 3
    assert len(visual["results"]) >= 3

    audio = data["audio"]
    assert audio["available"] is False
    assert audio["status"] == "unavailable"
    assert audio["results"] == []

    speech = data["speech"]
    assert speech["available"] is False
    assert speech["status"] == "unavailable"
    assert speech["segments"] == []

    # 4. Stage 2 Evidence & Trust Engine Outputs
    reliability = data["reliability"]
    assert reliability is not None
    assert reliability["level"] in {"OK", "LOW"}
    # Because synthetic video is 320x240 (<360), reliability should be LOW with diagnostic reasons
    assert reliability["level"] == "LOW"
    assert len(reliability["reasons"]) > 0

    evidence = data["evidence"]
    assert evidence is not None
    assert "visual" in evidence
    assert "audio" in evidence
    assert "provenance" in evidence
    assert evidence["provenance"]["state"] in {"NONE_FOUND", "FOUND", "UNAVAILABLE"}

    timeline = data["timeline"]
    assert isinstance(timeline, list)

    assessment = data["assessment"]
    assert assessment is not None
    assert assessment["media"] in {"LIKELY_MANIPULATED", "SUSPICIOUS", "NO_STRONG_EVIDENCE", "UNCERTAIN"}
    assert assessment["media"] != "AUTHENTIC"
    # Because reliability is LOW, media assessment should be UNCERTAIN
    assert assessment["media"] == "UNCERTAIN"
    assert "fraud" in assessment
    assert "action" in assessment

    # 5. Stage 3 Fraud Intent Outputs
    assert "fraud" in data
    assert data["fraud"]["level"] == "NOT_ASSESSABLE"
    assert data["fraud"]["categories"] == []
    assert data["fraud"]["requested_actions"] == []

    explanation = data["explanation"]
    assert isinstance(explanation, list)
    assert len(explanation) > 0

    limitations = data["limitations"]
    assert isinstance(limitations, list)
    assert len(limitations) > 0

    # 6. Privacy & Cleanup Verification: No leftover folders in temp dir
    analysis_temp_dir = settings.TEMP_DIR / data["id"]
    assert not analysis_temp_dir.exists(), f"Temporary directory {analysis_temp_dir} was not cleaned up!"


def test_post_analyses_corrupted_file(test_client: TestClient, temp_test_dir: Path):
    """Verifies that uploading a corrupt video file returns HTTP 422 with clean error."""
    corrupt_file = temp_test_dir / "bad_video.mp4"
    corrupt_file.write_bytes(b"INVALID_HEADER_GARBAGE_DATA" * 50)

    with open(corrupt_file, "rb") as f:
        response = test_client.post(
            "/api/analyses",
            files={"file": ("bad_video.mp4", f, "video/mp4")}
        )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "corrupt" in response.json()["detail"].lower() or "inspection failed" in response.json()["detail"].lower()


def test_post_analyses_with_audio_end_to_end(test_client: TestClient, synthetic_video_with_audio_path: Path):
    """
    End-to-end integration test for POST /api/analyses with video containing audio.
    Verifies:
      - Visual detector produces real/fake frame scores
      - Local audio detector produces windowed spoof scores
      - Faster-Whisper transcriber produces speech transcription and language detection
      - Stage 2 synthesis generates complete evidence matrix, timeline, and assessment
      - Stage 3 fraud intent engine evaluates speech and recommends action
    """
    with open(synthetic_video_with_audio_path, "rb") as video_file:
        response = test_client.post(
            "/api/analyses",
            files={"file": (synthetic_video_with_audio_path.name, video_file, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["video"]["audio_available"] is True

    # Visual branch
    assert data["visual"]["available"] is True
    assert data["visual"]["status"] == "completed"

    # Audio branch (Member 3)
    audio = data["audio"]
    assert audio["available"] is True
    assert audio["status"] == "completed"
    assert audio["model"] == "AASIST-ASVspoof2019-LA"
    assert audio["windows_analyzed"] >= 1
    assert len(audio["results"]) >= 1
    for win in audio["results"]:
        assert win["start_s"] >= 0.0
        assert win["end_s"] > win["start_s"]
        assert win["spoof_score"] is not None
        assert 0.0 <= win["spoof_score"] <= 1.0

    # Speech branch (Member 3)
    speech = data["speech"]
    assert speech["available"] is True
    assert speech["status"] == "completed"
    assert speech["model"] == "faster-whisper-base-int8"
    assert speech["language"] is not None
    assert isinstance(speech["segments"], list)

    # Stage 2 & 3 fields
    assert data["reliability"] is not None
    assert data["evidence"] is not None
    assert data["assessment"] is not None
    assert data["assessment"]["media"] in {"LIKELY_MANIPULATED", "SUSPICIOUS", "NO_STRONG_EVIDENCE", "UNCERTAIN"}
    assert data["assessment"]["media"] != "AUTHENTIC"
    assert data["assessment"]["fraud"] in {"LOW", "MEDIUM", "HIGH", "NOT_ASSESSABLE"}
    assert data["assessment"]["action"] in {"STOP_AND_VERIFY", "VERIFY", "CAUTION", "NO_ACTION_FLAGGED"}
    assert "fraud" in data
    assert isinstance(data["timeline"], list)
    assert isinstance(data["explanation"], list)
    assert isinstance(data["limitations"], list)


def test_get_analysis_by_id_and_not_found(test_client: TestClient, synthetic_video_path: Path):
    """
    Verifies that a completed analysis is retrievable via GET /api/analyses/{id},
    and that querying an unknown ID returns HTTP 404.
    """
    # 1. Upload video
    with open(synthetic_video_path, "rb") as video_file:
        post_res = test_client.post(
            "/api/analyses",
            files={"file": (synthetic_video_path.name, video_file, "video/mp4")}
        )
    assert post_res.status_code == 200
    created_id = post_res.json()["id"]

    # 2. Query by ID
    get_res = test_client.get(f"/api/analyses/{created_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == created_id
    assert retrieved["status"] == "completed"
    assert "assessment" in retrieved

    # 3. Non-existent ID returns 404
    missing_res = test_client.get("/api/analyses/00000000-0000-0000-0000-000000000000")
    assert missing_res.status_code == 404
