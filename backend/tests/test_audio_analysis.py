import math
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
import subprocess
from fastapi.testclient import TestClient

from app.core.config import settings
from app.utils.hashing import compute_sha256


@pytest.fixture
def synthetic_wav_audio_path(tmp_path: Path) -> Path:
    """Generates a 4.0-second 16kHz mono synthetic sine wave WAV audio file."""
    wav_path = tmp_path / "synthetic_voice.wav"
    sample_rate = 16000
    duration_s = 4.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    # 440 Hz pure tone + harmonic
    signal = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 880 * t)
    sf.write(str(wav_path), signal.astype(np.float32), sample_rate, format="WAV", subtype="PCM_16")
    return wav_path


@pytest.fixture
def synthetic_short_wav_audio_path(tmp_path: Path) -> Path:
    """Generates a 1.5-second short 16kHz WAV audio file (< 3.0s minimum threshold)."""
    wav_path = tmp_path / "short_voice.wav"
    sample_rate = 16000
    duration_s = 1.5
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(wav_path), signal.astype(np.float32), sample_rate, format="WAV", subtype="PCM_16")
    return wav_path


@pytest.fixture
def synthetic_mp3_audio_path(tmp_path: Path, synthetic_wav_audio_path: Path) -> Path:
    """Encodes a synthetic WAV audio file into MP3 format via FFmpeg."""
    mp3_path = tmp_path / "synthetic_voice.mp3"
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", str(synthetic_wav_audio_path),
        "-codec:a", "libmp3lame",
        "-b:a", "128k",
        str(mp3_path)
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        # Fallback to copy if libmp3lame is not built
        pytest.skip("FFmpeg MP3 encoder not available in test environment")
    return mp3_path


def test_post_standalone_audio_wav_end_to_end(test_client: TestClient, synthetic_wav_audio_path: Path):
    """
    End-to-end integration test for standalone WAV audio upload:
      - Media type correctly identified as AUDIO (skipping visual detector)
      - Video metadata is None and audio_metadata is populated
      - AASIST anti-spoofing sliding-window analysis executed
      - Faster-Whisper transcriber executed
      - Reliability Gate evaluates audio duration and detector status
      - Explanations explicitly note visual forensics is not applicable for audio-only
      - Ephemeral workspace cleaned up with zero data retention
    """
    expected_hash = compute_sha256(synthetic_wav_audio_path)

    with open(synthetic_wav_audio_path, "rb") as f:
        response = test_client.post(
            "/api/analyses",
            files={"file": ("synthetic_voice.wav", f, "audio/wav")}
        )

    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Structure Verification
    assert "id" in data
    assert data["status"] == "completed"
    assert "created_at" in data

    # 2. Input Classification & Metadata
    assert "input" in data
    assert data["input"]["media_type"] == "AUDIO"
    assert data["video"] is None
    
    assert data["audio_metadata"] is not None
    audio_meta = data["audio_metadata"]
    assert audio_meta["filename"] == synthetic_wav_audio_path.name
    assert audio_meta["sha256"] == expected_hash
    assert audio_meta["duration_s"] == pytest.approx(4.0, rel=0.1)
    assert audio_meta["sample_rate_hz"] == 16000
    assert audio_meta["channels"] == 1
    assert "pcm" in (audio_meta["codec"] or "").lower() or "wav" in (audio_meta["mime_type"] or "").lower()

    # 3. Visual detector is marked as not_applicable for audio
    visual = data["visual"]
    assert visual["available"] is False
    assert visual["status"] == "not_applicable"
    assert visual["frames_analyzed"] == 0
    assert visual["results"] == []

    # 4. Audio detector (AASIST) is completed
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

    # 5. Speech Transcriber (Whisper)
    speech = data["speech"]
    assert speech["available"] is True
    assert speech["status"] == "completed"
    assert speech["model"] == "faster-whisper-base-int8"

    # 6. Reliability Gate (4.0s >= 3.0s minimum threshold -> OK)
    reliability = data["reliability"]
    assert reliability is not None
    assert reliability["level"] == "OK"
    assert len(reliability["reasons"]) == 0

    # 7. Evidence Matrix
    evidence = data["evidence"]
    assert evidence is not None
    assert evidence["visual"]["level"] == "N/A"
    assert evidence["audio"]["level"] in {"LOW", "MEDIUM", "HIGH"}
    assert evidence["metadata"]["media_type"] == "AUDIO"
    assert evidence["metadata"]["duration_s"] == pytest.approx(4.0, rel=0.1)

    # 8. Media Assessment
    assessment = data["assessment"]
    assert assessment is not None
    assert assessment["media"] in {"LIKELY_MANIPULATED", "SUSPICIOUS", "NO_STRONG_EVIDENCE", "UNCERTAIN"}
    assert assessment["media"] != "AUTHENTIC"
    assert assessment["fraud"] in {"LOW", "MEDIUM", "HIGH", "NOT_ASSESSABLE"}
    assert assessment["action"] in {"STOP_AND_VERIFY", "VERIFY", "CAUTION", "NO_ACTION_FLAGGED"}

    # 9. Explanations
    explanation = data["explanation"]
    assert isinstance(explanation, list)
    assert any("not applicable for audio-only" in exp.lower() for exp in explanation)

    # 10. Guaranteed Workspace Cleanup
    analysis_temp_dir = settings.TEMP_DIR / data["id"]
    assert not analysis_temp_dir.exists()


def test_post_standalone_audio_mp3_end_to_end(test_client: TestClient, synthetic_mp3_audio_path: Path):
    """Verifies that MP3 audio uploads are supported and analyzed through the audio pipeline."""
    with open(synthetic_mp3_audio_path, "rb") as f:
        response = test_client.post(
            "/api/analyses",
            files={"file": ("synthetic_voice.mp3", f, "audio/mpeg")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["input"]["media_type"] == "AUDIO"
    assert data["video"] is None
    assert data["audio_metadata"] is not None
    assert data["audio_metadata"]["duration_s"] == pytest.approx(4.0, rel=0.15)
    assert data["visual"]["status"] == "not_applicable"
    assert data["audio"]["status"] == "completed"


def test_post_standalone_audio_short_duration_reliability_low(test_client: TestClient, synthetic_short_wav_audio_path: Path):
    """Verifies that audio shorter than 3.0s triggers Reliability Gate LOW."""
    with open(synthetic_short_wav_audio_path, "rb") as f:
        response = test_client.post(
            "/api/analyses",
            files={"file": ("short_voice.wav", f, "audio/wav")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["input"]["media_type"] == "AUDIO"
    assert data["reliability"]["level"] == "LOW"
    assert any("shorter than recommended minimum" in r.lower() for r in data["reliability"]["reasons"])
    assert data["assessment"]["media"] == "UNCERTAIN"


def test_post_standalone_audio_corrupted(test_client: TestClient, temp_test_dir: Path):
    """Verifies that uploading a corrupt audio file returns HTTP 422 with a clean error message."""
    corrupt_file = temp_test_dir / "bad_audio.wav"
    corrupt_file.write_bytes(b"INVALID_HEADER_GARBAGE_DATA" * 50)

    with open(corrupt_file, "rb") as f:
        response = test_client.post(
            "/api/analyses",
            files={"file": ("bad_audio.wav", f, "audio/wav")}
        )

    assert response.status_code == 422
    assert "detail" in response.json()
